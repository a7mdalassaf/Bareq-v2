# Rettlock Info System Architecture

## System Overview

This document provides a visual representation of the Rettlock Info system architecture, showing the relationships between different components and their interactions.

## Class Diagram

```mermaid
classDiagram
    class User {
        +id: Integer
        +username: String
        +password: String
        +is_current: Boolean
        +created_at: DateTime
        +to_dict()
    }
    
    class Guest {
        +id: Integer
        +name: String
        +passcode: String
        +start_date: DateTime
        +end_date: DateTime
        +lock_id: String
        +is_active: Boolean
        +created_at: DateTime
        +to_dict()
    }
    
    class LockDeviceMapping {
        +id: Integer
        +lock_id: String
        +device_id: String
        +lock_name: String
        +device_name: String
        +is_active: Boolean
        +created_at: DateTime
        +updated_at: DateTime
        +to_dict()
    }
    
    class TTLockManager {
        -client_id: String
        -client_secret: String
        -username: String
        -password: String
        -base_url: String
        -access_token: String
        +get_access_token()
        +get_lock_status(lock_id)
        +get_lock_list()
        +create_passcode(lock_id, name, start_date, end_date)
        +delete_passcode(lock_id, passcode_id)
        +get_passcode_list(lock_id)
    }
    
    class TuyaAPI {
        +CLIENT_ID: String
        +CLIENT_SECRET: String
        +DEVICE_ID: String
        +BASE_URL: String
        +get_token()
        +make_api_request(method, endpoint, body)
        +get_device_status()
        +is_device_on()
        +toggle_device(turn_on)
    }
    
    class TuyaAdapter {
        -client_id: String
        -client_secret: String
        -default_device_id: String
        -endpoint: String
        -_get_device_id(lock_id)
        -_get_token()
        +get_device_status(lock_id)
        +control_led(state, lock_id)
        +link_device(lock_id, device_id, lock_name, device_name)
        +unlink_device(lock_id)
    }
    
    class FlaskApp {
        +index()
        +check_lock()
        +add_guest()
        +delete_guest(guest_id)
        +sync_guests()
        +get_locks()
        +get_device_mappings()
        +link_device()
        +unlink_device(lock_id)
        +toggle_led()
        +update_readme()
        -check_active_passcodes()
        -update_led_status()
        -led_monitor()
    }
    
    FlaskApp --> TTLockManager : uses
    FlaskApp --> TuyaAdapter : uses
    TuyaAdapter --> TuyaAPI : depends on
    FlaskApp --> User : manages
    FlaskApp --> Guest : manages
    FlaskApp --> LockDeviceMapping : manages
    TTLockManager ..> Guest : creates/deletes passcodes
    TuyaAdapter ..> LockDeviceMapping : uses for device lookup
```

## Component Diagram

```mermaid
flowchart TB
    subgraph Frontend
        UI[Web Interface]
    end
    
    subgraph Backend
        WebApp[Flask Web App]
        TuyaModule[Tuya Integration]
        TTLockModule[TTLock Integration]
        DB[(SQLite Database)]
    end
    
    subgraph ExternalAPIs
        TuyaCloud[Tuya Cloud API]
        TTLockCloud[TTLock Cloud API]
    end
    
    UI <--> WebApp
    WebApp <--> DB
    WebApp <--> TuyaModule
    WebApp <--> TTLockModule
    TuyaModule <--> TuyaCloud
    TTLockModule <--> TTLockCloud
```

## Sequence Diagram: LED Control

```mermaid
sequenceDiagram
    actor User
    participant UI as Web Interface
    participant App as Flask App
    participant Adapter as TuyaAdapter
    participant API as TuyaAPI
    participant Cloud as Tuya Cloud

    User->>UI: Toggle LED button
    UI->>App: POST /toggle_led
    App->>Adapter: control_led(state)
    Adapter->>API: toggle_device(state)
    API->>Cloud: POST /v1.0/devices/{DEVICE_ID}/commands
    Cloud-->>API: Response
    API-->>Adapter: Result
    Adapter-->>App: Success/Failure
    App-->>UI: JSON Response
    UI-->>User: Update UI
```

## Directory Structure

```
rettlockinfo/
│
├── web_app.py             # Main Flask application
├── models.py              # Database models
├── tuya_api.py            # Core Tuya API integration module
├── tuya_adapter.py        # Adapter for Tuya API integration
├── smart_lock_manager.py  # TTLock integration 
├── utils.py               # Utility functions
│
├── templates/             # HTML templates
│   └── index.html         # Main UI template
│
├── instance/              # SQLite database
│   └── ttlock.db
│
├── static/                # Static assets
│   ├── css/
│   └── js/
│
├── archive/               # Archived code and files
│
└── docs/                  # Documentation
