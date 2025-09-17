# Web Redesign Client Scout

A Streamlit application for tracking and analyzing potential clients for web redesign businesses.

## Features

- **Dashboard**: View key metrics and visualizations of your client portfolio with tabbed analysis charts
- **Client Database**: Manage client information and track interactions
- **Website Analyzer**: Analyze websites to identify redesign opportunities
- **Export Data**: Export client data in various formats (Excel, CSV, JSON)
- **Settings**: Customize application settings and user profile

## Screenshots

(Screenshots will be added here)

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install streamlit pandas plotly openpyxl pillow requests beautifulsoup4
   ```
3. Run the application:
   ```
   streamlit run web_redesign_client_scout.py
   ```

## Building a standalone Windows executable

The project includes a helper script that wraps [PyInstaller](https://pyinstaller.org) to produce a single-file `.exe` that launches the Streamlit interface without requiring Python on the target machine.

1. Install the runtime dependencies and PyInstaller:
   ```
   pip install -r requirements.txt
   pip install pyinstaller
   ```
2. Build the executable:
   ```
   python build_executable.py
   ```
3. The bundled application will be available at `dist/WebRedesignClientScout.exe`. Copy the file to the target Windows machine and double-click it to launch the app.

The build script automatically includes the custom CSS theme, so the packaged app retains the polished UI from the development environment.

## Usage

The application helps web design agencies identify and track potential clients for website redesign services:

1. Use the Website Analyzer to evaluate potential client websites
2. Add promising prospects to your Client Database
3. Track interactions and status changes in the Client Database
4. Monitor your overall client portfolio in the Dashboard
5. Export data for reporting or use in other systems

## Technologies Used

- Streamlit
- Pandas
- Plotly
- BeautifulSoup
- Openpyxl

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
