# API Resilience Testing Framework

Automated testing framework for QA Home Assignment - Senior QA Engineer Assessment

## Overview

Comprehensive test automation suite for REST API resilience testing covering:
- JWT Bearer token authentication
- Rate limiting behavior (application and backend layers)
- Performance characteristics and latency patterns
- Error handling and edge cases
- Backend cold start and warmup processes

**Base URL:** `https://qa-home-assignment.magmadevs.com`

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Create and activate a virtual environment:**
   ```bash
    python3.12 -m venv venv
   
    # macOS/Linux:
    source venv/bin/activate

    # Windows:
    venv\Scripts\activate
   
   ```

3. **Install pip-tools (one-time setup):**
   ```bash
   pip install pip-tools
   ```

4. **Compile dependencies:**
   ```bash
    pip-compile requirements.in
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
6. **Verify installation:**
   ```bash
   python --version
   pytest --version
   allure --version
   ```

### Configuration

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your credentials:
   ```env
   INITIAL_REFRESH_TOKEN=your_token_here
   BASE_URL=https://qa-home-assignment.magmadevs.com
   SSL_VERIFY=false
   ```
   *Do not commit `.env` to version control.*

3. Verify.env is in .gitignore:


### Running Tests


* Run all tests
    ```bash
    pytest tests/ -v -s
    ```

* Run with coverage
    ```bash
    pytest --cov
    ```
* Run with Allure reporting
    ```bash
    # Run with Allure reporting
    pytest tests/ --alluredir=reports/allure-results
    
    # Open interactive Allure report
    allure serve reports/allure-results
    
    # Generate static HTML report
    allure generate reports/allure-results -o reports/allure-report --clean
    # Then open: open reports/allure-report/index.html (macOS)
        
    # One page HTML report
    pytest tests/ --html=reports/test_report.html --self-contained-html
    ```

## Dependency Management

This project uses `pip-tools` for dependency management:

- **`requirements.in`** - High-level dependencies with minimum versions
- **`requirements.txt`** - Auto-generated locked dependencies (exact versions)

### Updating Dependencies

1. **Edit `requirements.in`** to add/update packages
2. **Regenerate `requirements.txt`:**
   ```bash
   pip-compile requirements.in
   ```
3. **Install updated dependencies:**
   ```bash
   pip install -r requirements.txt
   ```


### First-Time Setup Checklist

- [ ] Verify `.env` is in `.gitignore`
- [ ] Create `.env` from `.env.example`
- [ ] Install dependencies from `requirements.txt`


## API Documentation

See `swagger.yaml` for full API specification.

## Tech Stack

### Test Automation

| **pytest 8.3+** | Testing framework |
| **requests 2.32+** | HTTP client library |
| **allure-pytest 2.13+** | Test reporting and visualization |
| **pytest-rerunfailures 15.0+** | Flaky test handling |

### Performance & Load Testing
| Tool | Purpose |
|------|---------|
| **locust 3.0+** | Load testing and performance profiling |

### API Exploration & Discovery
| Tool | Purpose |
|------|---------|
| **Postman** | Manual API exploration and collection building |
| **Swagger UI** | Interactive API documentation and testing |
| **curl** | Command-line HTTP requests and scripting |
| **Charles Proxy** | HTTP/HTTPS traffic inspection and debugging |

### Network & Infrastructure Analysis
| Tool | Purpose |
|------|---------|
| **nslookup** | DNS resolution verification |
| **traceroute** | Network path analysis and latency measurement |
| **openssl s_client** | SSL/TLS certificate and handshake inspection |

### Dependency Management
| Tool | Purpose |
|------|---------|
| **pip-tools** | Reproducible dependency management |