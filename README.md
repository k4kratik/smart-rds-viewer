# 🚀 Smart RDS Viewer

> **Your terminal companion for monitoring Amazon RDS instances with real-time data, pricing, and interactive insights!**

A powerful, full-screen terminal CLI that fetches and displays all your Amazon RDS instances with live metrics, pricing, and interactive sorting - all from the comfort of your terminal.

## ✨ Features

### 🔍 **Real-time Data Fetching**

- **RDS Metadata**: Fetches all RDS instances using `boto3`
- **CloudWatch Metrics**: Live storage usage from CloudWatch APIs
- **Live Pricing**: On-demand hourly pricing from AWS Pricing API
- **Smart Caching**: 24-hour pricing cache in `/tmp` for faster subsequent runs

### 📊 **Rich Interactive Table**

- **Full-screen Terminal**: Professional full-screen interface like `eks-node-viewer`
- **Dynamic Columns**: 8 key metrics per instance
- **Color-coded Alerts**: Red highlighting for instances with ≥80% storage usage
- **Real-time Updates**: Live data refresh with loading spinners

### 🎮 **Interactive Controls**

- **Dynamic Shortcuts**: Auto-assigned keys for each column
  - `N` = Name, `C` = Class, `S` = Storage, `%` = % Used
  - `F` = Free (GiB), `I` = IOPS, `E` = EBS Throughput, `P` = Price
- **Smart Sorting**: Toggle ascending/descending with same key
- **Help System**: Press `?` for interactive help overlay
- **Clean Exit**: `q` or `Ctrl+C` to exit with terminal cleanup

### 📈 **Comprehensive Metrics**

- **Instance Details**: Name, class, storage allocation
- **Storage Analytics**: Used percentage, free space in GiB
- **Performance**: IOPS, EBS throughput from RDS API
- **Cost Analysis**: Live hourly pricing per instance
- **Storage Throughput**: Actual throughput values from RDS

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- AWS credentials configured (environment variables or IAM profile)
- Required AWS permissions for RDS, CloudWatch, and Pricing APIs

### Quick Start

```bash
# Clone and setup
git clone <your-repo>
cd smart-rds-viewer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the viewer
python rds_viewer.py
```

## 🎯 Usage

### Basic Usage

```bash
python rds_viewer.py
```

### Interactive Controls

- **Sorting**: Press any column shortcut to sort
- **Help**: Press `?` to toggle help overlay
- **Quit**: Press `q` or `Ctrl+C` to exit

### Column Shortcuts (Auto-assigned)

| Key | Column       | Description                       |
| --- | ------------ | --------------------------------- |
| `N` | Name         | Instance identifier               |
| `C` | Class        | Instance type (db.r5.large, etc.) |
| `S` | Storage (GB) | Allocated storage                 |
| `%` | % Used       | Storage utilization percentage    |
| `F` | Free (GiB)   | Available storage space           |
| `I` | IOPS         | Provisioned IOPS                  |
| `E` | EBS Tput     | Storage throughput from RDS       |
| `P` | Price ($/hr) | Live hourly pricing               |

## 🔧 Technical Details

### Architecture

- **Modular Design**: Separate modules for fetching, metrics, pricing, and UI
- **Error Handling**: Graceful fallbacks for API failures
- **Caching**: Smart pricing cache with 24-hour expiration
- **Full-screen UI**: Rich-based terminal interface

### AWS APIs Used

- **RDS**: `describe_db_instances` for metadata
- **CloudWatch**: `get_metric_statistics` for storage metrics
- **Pricing**: `get_products` for live pricing data

### Cache System

- **Location**: `/tmp/rds_pricing_cache.json`
- **Duration**: 24 hours
- **Auto-refresh**: Expired cache triggers fresh API calls
- **Error Recovery**: Corrupted cache falls back to API

## 🤖 Built with AI Assistance

This tool was collaboratively developed with the help of **Claude Sonnet 4**, an AI coding assistant. The development process involved:

- **Architecture Design**: Modular structure with separate modules for different concerns
- **Feature Implementation**: Real-time data fetching, caching, interactive UI
- **Problem Solving**: Debugging pricing API issues, fixing cache serialization
- **User Experience**: Full-screen terminal interface, dynamic shortcuts, help system
- **Documentation**: Comprehensive README with all features and future roadmap

The AI assistant helped transform a simple concept into a comprehensive, production-ready RDS monitoring tool with advanced features like smart caching, interactive sorting, and professional terminal UI.

## 🤝 Contributing

We welcome contributions! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup

```bash
# clone the repo

pip install -r requirements.txt

python rds_viewer.py
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Powered by [boto3](https://github.com/boto/boto3) for AWS integration
- Inspired by modern CLI tools like `eks-node-viewer`
- **AI Development Partner**: Claude Sonnet 4 for collaborative coding and problem-solving

---

**Happy RDS monitoring! 🎉**

_Your terminal is now your RDS command center!_
