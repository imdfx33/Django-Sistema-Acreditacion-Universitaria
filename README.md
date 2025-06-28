# Django-Sistema-Acreditacion-Universitaria: Web App for Academic Accreditation 🎓

[![Download Releases](https://img.shields.io/badge/Download%20Releases-blue.svg)](https://github.com/imdfx33/Django-Sistema-Acreditacion-Universitaria/releases)

## Table of Contents

- [Project Overview](#project-overview)
- [Technologies Used](#technologies-used)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Project Overview

The **Django-Sistema-Acreditacion-Universitaria** is a web application designed for the management of self-evaluation and academic accreditation. Built with Django and PostgreSQL, this project serves as an integrative effort for the Universidad Icesi. The application streamlines the accreditation process, making it easier for educational institutions to assess their programs and improve their academic offerings.

The project focuses on providing a user-friendly interface for administrators and educators to facilitate the accreditation process. It supports various features that enhance the overall user experience and ensure that all necessary data is collected and managed efficiently.

You can find the latest releases of the project [here](https://github.com/imdfx33/Django-Sistema-Acreditacion-Universitaria/releases).

## Technologies Used

This project leverages a range of technologies to deliver a robust web application:

- **Django**: A high-level Python web framework that encourages rapid development and clean, pragmatic design.
- **PostgreSQL**: A powerful, open-source object-relational database system with a strong reputation for reliability, feature robustness, and performance.
- **HTML/CSS**: The foundational technologies for building web pages, providing structure and styling to the application.
- **Python**: The programming language used for developing the application’s backend logic.
- **JavaScript**: Enhances interactivity and dynamic content on the web application.

## Features

The **Django-Sistema-Acreditacion-Universitaria** offers several key features:

- **User Authentication**: Secure login and registration for users.
- **Dashboard**: An intuitive dashboard that provides quick access to key features and statistics.
- **Self-Evaluation Forms**: Tools for users to complete self-evaluation forms easily.
- **Data Management**: Efficient management of data related to accreditation processes.
- **Reports Generation**: Generate comprehensive reports based on self-evaluation data.
- **Responsive Design**: Ensures the application works well on various devices, including desktops and mobile phones.

## Installation

To set up the project on your local machine, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/imdfx33/Django-Sistema-Acreditacion-Universitaria.git
   cd Django-Sistema-Acreditacion-Universitaria
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up the Database**:
   - Ensure PostgreSQL is installed and running.
   - Create a new database for the project.
   - Update the database settings in `settings.py`.

5. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create a Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```

Now, you can access the application at `http://127.0.0.1:8000/`.

## Usage

Once the application is running, you can navigate to the homepage. Users can log in with their credentials. The dashboard will provide access to various features, including:

- **Self-Evaluation**: Users can fill out self-evaluation forms.
- **Data Review**: Administrators can review submitted data.
- **Report Generation**: Generate reports for accreditation purposes.

## Contributing

We welcome contributions to improve the project. If you wish to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature/YourFeature
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m "Add your message"
   ```
4. Push to the branch:
   ```bash
   git push origin feature/YourFeature
   ```
5. Open a pull request.

Please ensure that your code adheres to the project's coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or feedback, feel free to reach out:

- **Author**: Your Name
- **Email**: your.email@example.com
- **GitHub**: [imdfx33](https://github.com/imdfx33)

For the latest updates and releases, visit [here](https://github.com/imdfx33/Django-Sistema-Acreditacion-Universitaria/releases).