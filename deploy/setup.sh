#!/bin/bash
# CHAT Streamlit App - EC2 Setup Script (Offline/GovCloud Version)
# Run this script on a fresh Amazon Linux 2023 EC2 instance
#
# PREREQUISITES:
# 1. Upload chat-packages/ folder containing pre-downloaded Python wheels to ~/chat-packages/
# 2. Upload app.py, requirements.txt to current directory
# 3. Upload the chat/ package directory
# 4. Run: chmod +x setup.sh && ./setup.sh

set -e

APP_DIR="/opt/chat"
APP_USER="chat"
APP_PORT="8502"
PACKAGES_DIR="/home/ec2-user/chat-packages"

echo "=== CHAT Deployment Script (Offline Mode - GovCloud Edition) ==="

# Check if we're doing offline install
OFFLINE_MODE=false
if [ -d "$PACKAGES_DIR" ]; then
    OFFLINE_MODE=true
    echo "Offline packages found - will install from local packages"
else
    echo "No offline packages found - will install from internet"
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS"

# Install dependencies based on OS
if [ "$OS" = "amzn" ]; then
    echo "Installing dependencies for Amazon Linux..."
    sudo yum update -y
    sudo yum install -y python3.11 python3.11-pip git
elif [ "$OS" = "ubuntu" ]; then
    echo "Installing dependencies for Ubuntu..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-pip python3.11-venv git
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Create app user if it doesn't exist
if ! id "$APP_USER" &>/dev/null; then
    echo "Creating application user: $APP_USER"
    sudo useradd -r -s /bin/false $APP_USER
fi

# Create app directory
echo "Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR

# Copy application files (assumes files are in current directory)
echo "Copying application files..."
sudo cp app.py $APP_DIR/
sudo cp requirements.txt $APP_DIR/

# Copy the chat package directory
if [ -d chat ]; then
    sudo cp -r chat $APP_DIR/
fi
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# Create virtual environment
echo "Setting up Python virtual environment..."
sudo -u $APP_USER python3.11 -m venv $APP_DIR/venv

if [ "$OFFLINE_MODE" = true ]; then
    # Copy packages to app directory so chat user can access them
    echo "Copying packages to app directory..."
    sudo cp -r $PACKAGES_DIR $APP_DIR/packages
    # Remove any .tar.gz source files that might cause issues
    sudo rm -f $APP_DIR/packages/*.tar.gz
    sudo chown -R $APP_USER:$APP_USER $APP_DIR/packages

    # Install from local packages
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --no-index --find-links=$APP_DIR/packages --upgrade pip
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --no-index --find-links=$APP_DIR/packages -r $APP_DIR/requirements.txt
else
    # Install from internet
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt
fi

# Create Streamlit config directory
echo "Configuring Streamlit..."
sudo mkdir -p $APP_DIR/.streamlit
sudo tee $APP_DIR/.streamlit/config.toml > /dev/null <<EOF
[server]
port = $APP_PORT
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
EOF
sudo chown -R $APP_USER:$APP_USER $APP_DIR/.streamlit

# Create AWS credentials directory
echo "Setting up AWS credentials directory..."
sudo mkdir -p $APP_DIR/.aws
sudo chown $APP_USER:$APP_USER $APP_DIR/.aws
sudo chmod 700 $APP_DIR/.aws

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/chat.service > /dev/null <<EOF
[Unit]
Description=CHAT AI Assistant Streamlit App
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="HOME=$APP_DIR"
Environment="AWS_SHARED_CREDENTIALS_FILE=$APP_DIR/.aws/credentials"
Environment="CHAT_DB_PATH=$APP_DIR/chat.db"
Environment="CHAT_JWT_SECRET=$JWT_SECRET"
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port $APP_PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable chat
sudo systemctl start chat

echo ""
echo "=== Setup Complete ==="
echo "The CHAT app is now running on port $APP_PORT"
echo ""
echo "Next steps:"
echo "1. Configure AWS credentials for the chat user:"
echo "   sudo nano $APP_DIR/.aws/credentials"
echo ""
echo "   Add the following content:"
echo "   [default]"
echo "   aws_access_key_id = YOUR_ACCESS_KEY"
echo "   aws_secret_access_key = YOUR_SECRET_KEY"
echo ""
echo "2. Set proper permissions:"
echo "   sudo chown -R $APP_USER:$APP_USER $APP_DIR/.aws"
echo "   sudo chmod 600 $APP_DIR/.aws/credentials"
echo ""
echo "3. Restart the service:"
echo "   sudo systemctl restart chat"
echo ""
echo "4. Check service status: sudo systemctl status chat"
echo "5. View logs: sudo journalctl -u chat -f"
echo "6. Access the app at: http://<your-ec2-ip>:$APP_PORT"
