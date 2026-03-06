# TTLock API Integration Documentation

## Overview

This document provides detailed information about the TTLock API integration in the RettLockInfo application, including recent fixes, best practices, and troubleshooting guidance.

## API Endpoints and Authentication

### Base URL and Endpoints

The TTLock API uses the following base URL and endpoints:

- **Base URL**: `https://euapi.ttlock.com`
- **Authentication**: `/oauth2/token`
- **Lock List**: `/v3/lock/list`
- **Lock Status**: `/v3/lock/queryOpenState`
- **Lock Details**: `/v3/lock/detail`

### Authentication Process

The TTLock API uses OAuth2 for authentication. The process involves:

1. **Token Request**:
   ```python
   url = f"{base_url}/oauth2/token"
   data = {
       'clientId': client_id,
       'clientSecret': client_secret,
       'username': username,
       'password': password_md5  # MD5 hash in lowercase
   }
   headers = {
       "Content-Type": "application/x-www-form-urlencoded"
   }
   response = requests.post(url, data=data, headers=headers)
   ```

2. **Token Response**:
   ```json
   {
     "access_token": "6b3d45bf992e2a0d64e8c2930e5b291e",
     "refresh_token": "dca1dd6ed430518c8c43c06f222b0ef3",
     "uid": 19840368,
     "openid": 1593852163,
     "scope": "user,key,room",
     "token_type": "Bearer",
     "expires_in": 6017724
   }
   ```

3. **Token Usage**:
   The access token is included in all subsequent API requests as the `accessToken` parameter.

## Recent Fixes

The following issues were identified and fixed in the TTLock API integration:

1. **Incorrect API Base URL**:
   - Changed from `https://api.ttlock.com/v3` to `https://euapi.ttlock.com`
   - Ensured all endpoint paths include the `/v3` prefix

2. **Incorrect Request Format**:
   - Updated all API requests to use the correct content type header: `application/x-www-form-urlencoded`
   - Changed from using `params` to using `data` for POST requests
   - Ensured GET requests use `params` correctly

3. **Authentication Issues**:
   - Fixed the password hashing to ensure MD5 is in lowercase format (32 characters)
   - Removed unnecessary `grant_type` parameter from token requests

4. **Error Handling and Logging**:
   - Added comprehensive logging for all API requests and responses
   - Implemented proper error handling for API responses
   - Sanitized sensitive data in logs

## Best Practices

### API Request Format

All TTLock API requests should follow these guidelines:

1. **Authentication**:
   - Use POST with data parameter
   - Include Content-Type header: `application/x-www-form-urlencoded`
   - Hash passwords using MD5 in lowercase

2. **Lock Operations**:
   - Use POST with data parameter for write operations
   - Use GET with params for read operations
   - Always include the current timestamp in milliseconds as the `date` parameter

3. **Error Handling**:
   - Check HTTP status code (200 for success)
   - Check response JSON for error codes and messages
   - Implement retry logic for transient errors

### Credential Management

Credentials should be stored securely and retrieved using the CredentialService:

```python
client_id = CredentialService.get_credential('ttlock', 'api', 'client_id')
client_secret = CredentialService.get_credential('ttlock', 'api', 'client_secret')
```

Never hardcode credentials in the application code.

## Troubleshooting

### Common Issues and Solutions

1. **Authentication Failures**:
   - Verify that the client ID and client secret are correct
   - Ensure the username and password are valid
   - Check that the password is properly hashed to MD5 in lowercase

2. **API Request Errors**:
   - Verify the correct base URL and endpoint paths
   - Check that the request method (GET/POST) matches the endpoint requirements
   - Ensure the content type header is set correctly
   - Validate that all required parameters are included

3. **No Locks Found**:
   - Verify that the account has locks associated with it
   - Check that the token is valid and not expired
   - Ensure the correct client ID is being used

### Debugging Tools

1. **Test Scripts**:
   - `test_ttlock_api.py`: Tests basic API connectivity
   - `test_ttlock_integration.py`: Tests the full integration with the application

2. **Logging**:
   - Enable DEBUG level logging to see detailed API request and response information
   - Check the application logs for error messages and warnings

## Architecture

The TTLock integration follows a layered architecture:

1. **TTLockAccountManager**: Manages multiple TTLock accounts and their credentials
   - Handles token retrieval and management
   - Provides methods for lock retrieval and operations
   - Implements caching for improved performance

2. **TTLockAdapter**: Provides a high-level interface for the application
   - Uses the account manager for low-level API operations
   - Abstracts away the complexity of multiple accounts
   - Implements business logic for lock operations

This separation of concerns ensures maintainability and extensibility of the TTLock integration.

## Testing

Comprehensive testing has been implemented to ensure the reliability of the TTLock integration:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test the interaction between components
3. **API Tests**: Test the communication with the TTLock API
4. **End-to-End Tests**: Test the full application workflow

Regular testing helps identify and fix issues before they affect users.

## Future Improvements

Potential areas for future improvement include:

1. **Enhanced Caching**: Implement more sophisticated caching strategies
2. **Rate Limiting**: Add more robust rate limiting to avoid API throttling
3. **Offline Mode**: Implement offline mode for when the API is unavailable
4. **Monitoring**: Add monitoring and alerting for API health and performance

## Conclusion

The TTLock API integration has been significantly improved with the recent fixes. By following the best practices outlined in this document, the integration will continue to function reliably and efficiently.
