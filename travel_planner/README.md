# ✈️ Travel Planner

A modern, AI-powered travel planning application built with Streamlit, designed to help users find and book flights, create travel itineraries, and get personalized recommendations.

## 🚀 Features

- **Smart Flight Search**: Find flights with powerful filtering and sorting options
- **AI-Powered Itineraries**: Generate personalized travel plans using AI
- **Responsive Design**: Works on desktop and mobile devices
- **Offline Support**: Cache flight data for faster searches
- **PDF Export**: Save and share your travel plans
- **Multi-language Support**: Built with internationalization in mind

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/travel-planner.git
   cd travel-planner
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Update the API keys and settings as needed

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# API Keys (get these from the respective services)
AMADEUS_API_KEY=your_amadeus_api_key
AMADEUS_API_SECRET=your_amadeus_api_secret
GEMINI_API_KEY=your_gemini_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_access_key

# Application Settings
LOG_LEVEL=INFO
CACHE_TTL_FLIGHTS=3600  # 1 hour
CACHE_TTL_IMAGES=86400  # 24 hours
HTTP_TIMEOUT=10.0
MAX_RETRIES=3

# Paths (relative to project root)
ASSETS_DIR=assets
DATA_DIR=data
LOG_FILE=logs/app.log
```

## 📂 Project Structure

```
travel_planner/
├── .env.example           # Example environment variables
├── app.py                # Main application entry point
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── config/               # Configuration files
│   ├── __init__.py
│   ├── settings.py       # Application settings
│   └── log_config.py     # Logging configuration
├── schemas/              # Pydantic models
│   ├── __init__.py
│   ├── flight.py        # Flight data models
│   ├── itinerary.py     # Itinerary data models
│   └── search.py        # Search query models
├── services/             # Business logic and external services
│   ├── __init__.py
│   ├── amadeus_service.py  # Flight search service
│   ├── gemini_service.py   # AI itinerary generation
│   ├── unsplash_service.py # Image search service
│   └── flight_faker.py     # Mock flight data for development
├── utils/                # Utility functions
│   ├── __init__.py
│   ├── airport_loader.py  # Airport data loading and search
│   ├── pdf_generator.py   # PDF generation for itineraries
│   └── helpers.py         # Helper functions
├── assets/               # Static assets
│   ├── css/             # Custom styles
│   └── images/          # Static images
└── tests/               # Unit and integration tests
    ├── __init__.py
    ├── test_services.py
    └── test_utils.py
```

## 🧪 Testing

Run the test suite with pytest:

```bash
pytest tests/ -v
```

For test coverage report:

```bash
pytest --cov=travel_planner tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ using [Streamlit](https://streamlit.io/)
- Flight data powered by [Amadeus for Developers](https://developers.amadeus.com/)
- AI capabilities powered by [Google Gemini](https://ai.google/)
- Beautiful images from [Unsplash](https://unsplash.com/developers)
