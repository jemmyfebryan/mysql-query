# Changelog

All notable changes to this project will be documented in this file.  
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

---

## [1.3.0] - 2026-02-23
### Added
- Add support for Microsoft SQL Database (MSSQL).

### Changed
- Update `.config.example.json` for Microsoft SQL Database configuration.

---

## [1.2.0] - 2026-02-09
### Added
- Add user password credential when try to query (see .env.example).

### Changed
- Update `.env.example` for password manager.

---

## [1.1.0] - 2025-08-22
### Added
- Support for multiple database connections via `config.json` (see config.json.example).

### Changed
- Maintained backward compatibility for single DB connection via `.env`.
- The single DB connection endpoint `/secure_query` will be included to `/query`, with an optional `api_key` parameter in the request payload to indicate a secure query connection.

---

## [1.0.0] - 2025-07-30
### Added
- Initial project setup.
