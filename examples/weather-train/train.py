import time

import torch
import torch.nn as nn

FEATURES = ["humidity", "wind_speed", "pressure", "cloud_cover", "month"]
NUM_SAMPLES = 10_000
EPOCHS = 200
LR = 0.01
BATCH_SIZE = 256


def generate_data(n: int, device: torch.device):
    torch.manual_seed(42)
    humidity = torch.rand(n, 1, device=device) * 100
    wind_speed = torch.rand(n, 1, device=device) * 50
    pressure = 950 + torch.rand(n, 1, device=device) * 80
    cloud_cover = torch.rand(n, 1, device=device) * 100
    month = torch.randint(1, 13, (n, 1), device=device, dtype=torch.float32)

    # Temperature formula: seasonal base + feature effects + noise
    seasonal = 15 + 12 * torch.sin((month - 4) * 3.14159 / 6)
    temp = (
        seasonal
        + 0.1 * humidity
        - 0.15 * wind_speed
        + 0.05 * (pressure - 1013)
        - 0.08 * cloud_cover
        + torch.randn(n, 1, device=device) * 2
    )

    X = torch.cat([humidity, wind_speed, pressure, cloud_cover, month], dim=1)
    return X, temp


class WeatherNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**2:.0f} MB")

    print(f"\nGenerating {NUM_SAMPLES} synthetic weather samples...")
    X, y = generate_data(NUM_SAMPLES, device)

    split = int(0.8 * NUM_SAMPLES)
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    model = WeatherNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()

    print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")
    print(f"Training: {EPOCHS} epochs, batch_size={BATCH_SIZE}, lr={LR}\n")

    start = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for i in range(0, len(X_train), BATCH_SIZE):
            xb = X_train[i : i + BATCH_SIZE]
            yb = y_train[i : i + BATCH_SIZE]

            pred = model(xb)
            loss = loss_fn(pred, yb)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        if epoch % 20 == 0 or epoch == 1:
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val)
                val_loss = loss_fn(val_pred, y_val).item()
            print(
                f"Epoch {epoch:3d}/{EPOCHS}  "
                f"train_loss={epoch_loss / n_batches:.4f}  "
                f"val_loss={val_loss:.4f}"
            )

    elapsed = time.time() - start
    print(f"\nTraining completed in {elapsed:.1f}s")

    model.eval()
    with torch.no_grad():
        val_pred = model(X_val)
        val_loss = loss_fn(val_pred, y_val).item()
        mae = (val_pred - y_val).abs().mean().item()

    print(f"Final val MSE:  {val_loss:.4f}")
    print(f"Final val MAE:  {mae:.2f}°C")

    print("\nSample predictions (first 5 validation):")
    print(
        f"{'Humidity':>8} {'Wind':>6} {'Press':>7} {'Cloud':>6} {'Month':>5} | {'Actual':>7} {'Pred':>7}"
    )
    print("-" * 65)
    for i in range(5):
        row = X_val[i]
        actual = y_val[i].item()
        pred = val_pred[i].item()
        print(
            f"{row[0]:8.1f} {row[1]:6.1f} {row[2]:7.1f} {row[3]:6.1f} {row[4]:5.0f} "
            f"| {actual:7.2f} {pred:7.2f}"
        )

    torch.save(model.state_dict(), "/tmp/weather_model.pt")
    print("\nModel saved to /tmp/weather_model.pt")


if __name__ == "__main__":
    main()
