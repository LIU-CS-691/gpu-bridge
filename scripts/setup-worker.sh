#!/bin/bash
set -e

echo "Installing Docker..."
curl -fsSL https://get.docker.com | sh

echo "Installing NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker

echo "Starting Docker..."
dockerd &
sleep 3

echo "Verifying GPU in Docker..."
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

echo "Installing gpu-worker..."
pip install gpu-worker

echo ""
echo "=== Setup complete! ==="
echo "Now run:"
echo "  export GPU_BRIDGE_INVITE=\"<your_worker_invite_token>\""
echo "  gpu-worker register --name \"RunPod GPU\""
echo "  gpu-worker start --worker-id <ID> --gpu"
