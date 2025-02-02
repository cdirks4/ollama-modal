#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up development environment for Ollama-Modal...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Create virtual environment
echo -e "\n${BLUE}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
echo -e "\n${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "\n${BLUE}Installing requirements...${NC}"
pip install -r requirements.txt

# Initialize Modal (if not already set up)
echo -e "\n${GREEN}Setup complete! To finish configuration:${NC}"
echo -e "1. Run: ${BLUE}modal token new${NC}"
echo -e "2. Follow the authentication steps in your browser"
echo -e "\nTo activate the virtual environment in the future, run:"
echo -e "${BLUE}source venv/bin/activate${NC}"
echo -e "\nTo run the interactive chat:"
echo -e "${BLUE}modal run ollama-modal.py${NC}" 