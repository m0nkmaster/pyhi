# Development Roadmap

This document outlines planned features and improvements for the Voice Assistant project. To contribute to any of these items, please open an issue or pull request.

## 🎯 Planned Features

### Smart Home Integration
- [ ] Smart switch support (e.g., Smart Life)

### Music Playback
- [ ] Youtube Music integration
- [ ] Spotify integration

### Hardware Support
- [ ] Physical button activation
- [ ] Raspberry Pi port

### Core Improvements
- [ ] Local wake word detection (reduce API dependency)
  - Investigate Porcupine/Snowboy alternatives?
  - Local model?
- [ ] Webhook system for custom integrations
  - REST API endpoint support
- [ ] Stateful conversation context management

## 🔄 In Progress

- Pi support
- Initial polishing

## ✅ Completed

- Basic voice interaction
- OpenAI API integration
- Audio recording/playback

## 📋 Technical Debt & Improvements

- [ ] Test coverage (slap on the wrist for not doing TDD)
- [ ] Performance optimization for wake word detection
- [ ] Better error handling and recovery
- [ ] Docker containerization

## 💡 Future Ideas

- Web interface for configuration
- Multi-user voice recognition (profiles)
- Offline mode
- Extensible plugin system
