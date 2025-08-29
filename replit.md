# Overview

CineForge is a comprehensive AI-powered filmmaking pipeline built on Google Cloud Platform that transforms written stories into complete films. The application follows a multi-stage "Story to Screen" workflow that includes narrative analysis, screenplay generation, storyboard creation, visual asset generation using Imagen, video synthesis using Veo, and final film assembly. The system is designed with a human-in-the-loop approach, allowing for review and approval at each critical stage of the creative process.

The pipeline consists of five main stages: narrative deconstruction (analyzing raw text into structured JSON schemas), screenplay and storyboard generation, visual asset creation (character portraits, environment plates, and storyboard images), video synthesis (animating storyboard images into video clips), and final assembly using FFmpeg. The application supports multiple visual styles and provides both synchronous and asynchronous processing capabilities.

## Current Status
**✅ Successfully configured for Replit environment**
- Frontend (Streamlit) running on port 5000 with proper host configuration
- All Python dependencies installed and configured
- Redis server available for task queue processing
- Environment configuration templates provided
- Deployment configuration set for production

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes (August 2025)

## Replit Environment Setup Completed
- **Frontend Configuration**: Modified Streamlit app to run on port 5000 with 0.0.0.0 host binding and proper CORS/security settings for Replit's iframe-based proxy
- **Dependency Management**: Installed all required Python packages including Google Cloud AI Platform, Streamlit, FastAPI, Celery, and Redis
- **Import Fixes**: Resolved module import issues between ui/app.py and api.py by adding proper path resolution
- **Redis Installation**: Configured Redis server for Celery task queue processing
- **Environment Templates**: Created env_sample.txt with proper configuration examples for Google Cloud credentials
- **Deployment Configuration**: Set up autoscale deployment target with Streamlit as the primary service
- **Error Handling**: Added graceful fallbacks for missing modules and improved error handling

# System Architecture

## Pipeline Architecture
The system follows a linear pipeline pattern with distinct, well-defined stages that can be executed independently or as part of a complete workflow. Each stage produces specific outputs that serve as inputs for subsequent stages, enabling modular development and debugging. The pipeline maintains state through either JSON files or SQLite database, allowing for pause-and-resume functionality and progress tracking.

## Frontend Architecture
The user interface is built with Streamlit, providing an intuitive web-based interface for managing the filmmaking pipeline. The UI allows users to upload stories, configure project settings (GCP credentials, visual styles), monitor pipeline progress, and review outputs at each stage. The interface supports both step-by-step execution and full pipeline automation, with real-time status updates and error handling.

## Backend Architecture
The backend uses FastAPI to provide RESTful endpoints for pipeline operations. The system supports both synchronous execution (for immediate processing) and asynchronous execution using Celery with Redis as the message broker. This dual-mode approach allows for quick testing and development while supporting long-running operations for production use. The backend integrates directly with Google Cloud Vertex AI services for AI model access.

## State Management
Project state is managed through a flexible backend system that supports both JSON file storage (for development) and SQLite database (for production). The state tracks pipeline progress, stores intermediate outputs, manages error conditions, and maintains project metadata. This design allows for easy migration between storage backends and supports concurrent project management.

## Configuration System
The application uses a hierarchical configuration system with JSON-based config files that can be extended with YAML support. Configuration covers Vertex AI model settings, generation parameters, output paths, and visual style definitions. The system supports environment variable overrides and provides sensible defaults for rapid deployment.

## Content Generation Pipeline
Each pipeline stage is implemented as a modular component that can be executed independently. The narrative deconstruction stage uses Gemini models to analyze stories and produce structured schemas. Screenplay and storyboard generation leverage the schemas to create formatted scripts and detailed shot descriptions. Visual asset generation uses Imagen for creating character portraits, environment plates, and storyboard images with consistent styling. Video synthesis employs Veo to animate storyboard images into video clips with motion and transitions.

## Error Handling and Resilience
The system implements comprehensive error handling with automatic retry mechanisms for transient failures. Celery tasks support configurable retry policies with exponential backoff. The state management system tracks errors and allows for manual intervention and re-execution of failed stages. The modular design enables partial pipeline execution and selective regeneration of content.

# External Dependencies

## Google Cloud Platform Services
- **Vertex AI**: Core AI platform providing access to Gemini models for text generation (narrative analysis, screenplay writing), Imagen for image generation (character portraits, environments, storyboard images), and Veo for video synthesis
- **Google Cloud Storage**: File storage for generated assets and intermediate outputs
- **Google Cloud Text-to-Speech**: Voice generation for dialogue and narration
- **Google Cloud Vision**: Image analysis and processing capabilities

## Infrastructure and Deployment
- **Docker**: Containerization for consistent deployment across environments
- **Redis**: Message broker for Celery task queue and caching layer
- **SQLite**: Local database for project state management in production mode
- **FFmpeg**: Video processing and final film assembly

## Python Libraries and Frameworks
- **Streamlit**: Web UI framework for the user interface
- **FastAPI**: Modern web framework for REST API endpoints
- **Celery**: Distributed task queue for asynchronous processing
- **Uvicorn/Gunicorn**: ASGI/WSGI servers for production deployment
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for API interactions

## Development and Configuration
- **PyYAML**: Configuration file parsing (optional)
- **python-multipart**: File upload handling in FastAPI
- **pydub**: Audio processing utilities
- **ffmpeg-python**: Python wrapper for FFmpeg operations

## Authentication and Security
The system relies on Google Cloud Application Default Credentials (ADC) for authentication, supporting both local development (via gcloud CLI) and production deployment (via service accounts). Environment variables manage sensitive configuration data, and the Docker setup includes proper credential mounting for secure access to Google Cloud services.