# 🔐 Threat Intelligence Aggregator - Backend

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)

> 🔍 Automated scraping of 20+ top cybersecurity news sources in one place

## ✨ Features

- 🤖 Automated scraping from major security news sites
- 🎯 Smart duplicate detection
- 📊 Configurable per-source rules
- 🪵 Detailed logging
- 🐳 Docker ready

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/YashitaCodes/threatintel-backend.git
cd threatintel-backend

# Start with Docker
docker-compose up -d
```

## 📁 Structure

```
.
├── config/          # Configuration files
├── data/           # Scraped articles
├── logs/           # Application logs
└── src/            # Source files
```

## ⚙️ Configuration

Edit `config/scraper_config.json` to customize sources and selectors.

## 📝 Logs

```bash
# View logs
docker-compose logs -f
```

## 🛠️ Troubleshooting

- 💾 **Memory Issues**: Adjust limits in docker-compose.yml
- 🌐 **Network Issues**: Check firewall/proxy settings
- 🔍 **Scraping Fails**: Verify source availability

## 🤝 Contributing

1. Fork it
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -am 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Create Pull Request

## 📜 License

MIT © Yashita Mittal

---
Made with ❤️ by Yashita Mittal
