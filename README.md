<!-- PROJECT INTRO -->

OrpheusDL - Napster
=================

A Napster module for the OrpheusDL modular archival music program. Note that this is a general Napster downloader, so it supports all applications that use the Napster API, such as their own apps (such as their main apps, ALDI Life Musik, Vivo Musica, and mora qualitas), or apps that directly use the Napster API. Therefore, it does not come with API keys for each preinstalled, but some are provided below.

[Report Bug](https://github.com/yarrm80s/orpheusdl-napster/issues)
·
[Request Feature](https://github.com/yarrm80s/orpheusdl-napster/issues)


## Table of content

- [About OrpheusDL - Napster](#about-orpheusdl-napster)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
    - [Global](#global)
    - [Napster](#napster)
        - [Example Configurations](#example-configurations)
- [Contact](#contact)



<!-- ABOUT ORPHEUS -->
## About OrpheusDL - Napster

OrpheusDL - Napster is a module written in Python which allows archiving from **Napster** for the modular music archival program.


<!-- GETTING STARTED -->
## Getting Started

Follow these steps to get a local copy of Orpheus up and running:

### Prerequisites

* Already have [OrpheusDL](https://github.com/yarrm80s/orpheusdl) installed

### Installation

1. Clone the repo inside the folder `orpheus.py` is stored in with the following command:
   ```sh
   git clone https://github.com/yarrm80s/orpheusdl-napster.git modules/napster
   ```
2. Execute:
   ```sh
   python orpheus.py settings refresh
   ```
3. Now the `config/settings.json` file should be updated with the napster settings

<!-- USAGE EXAMPLES -->
## Usage

Just call `orpheus.py` with any link you want to archive:

```sh
python orpheus.py http://app.napster.com/artist/alan-walker/album/darkside-single/track/darkside
```

<!-- CONFIGURATION -->
## Configuration

You can customize every module from Orpheus individually and also set general/global settings which are active in every
loaded module. You'll find the configuration file here: `config/settings.json`

### Global

```json
"global": {
    "general": {
        ...
        "download_quality": "lossless"
    },
    ...
}
```

`download_quality`: Choose one of the following settings:
* "hifi": FLAC up to 24bit
* "lossless": FLAC up to 24bit (Napster does not separate the two)
* "high": AAC 320 kbps
* "medium": AAC 192 kbps
* "low": MP3 128 kbps
* "minimum": HE-AAC 64 kbps

### Napster
```json
 "napster": {
    "api_key": "",
    "customer_secret": "",
    "requested_netloc": "",
    "username": "",
    "password": ""
}
```
`api_key`: Enter a valid API client key

`customer_secret`: Enter a valid API client secret corresponding to the `api_key`

`requested_netloc`: Which website the module should respond to, e.g. `napster` for napster.com

`username`: Your account username matching the API keys you are using

`password`: Your account password corresponding to all of the above

#### Example Configurations
Napster's main app:
```json
"api_key": "ZTJlOWNhZGUtNzlmZS00ZGU2LTkwYjMtZDk1ODRlMDkwODM5",
"customer_secret": "MTRjZTVjM2EtOGVlZi00OTU3LWFmNjktNTllODFhNmYyNzI5",
"requested_netloc": "napster"
```

<!-- Contact -->
## Contact

Yarrm80s - [@yarrm80s](https://github.com/yarrm80s)

Project Link: [OrpheusDL Napster Public GitHub Repository](https://github.com/yarrm80s/orpheusdl-napster)
