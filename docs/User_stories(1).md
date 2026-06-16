# User stories

1)

As a new user
I want to create an account
So that I can use the system

Acceptance Criteria
- The user can create an account
- The email must be unique
- The account is saved in the system

2) 

As a registered user
I want to log in to my account
So that I can access the system

Acceptance Criteria
- The user can log in
- Upon successful login, a token is issued
- If the login information is invalid, an error is displayed

3)

As an authenticated user
I want to receive an access token
So that I can securely interact with protected resources

Acceptance Criteria
- A token is issued after successful authorization
- The token allows access to protected resources
- An invalid token is rejected

4) 

As an authenticated user
I want to create a new secret
So that I can securely store sensitive information

Acceptance Criteria
- The user can create a new secret
- The secret is stored in the system
- Data is encrypted before storage

5) 

As a secret owner
I want to see all available secrets
So that I can quickly find the information I need

Acceptance Criteria
- The user can see a list of their secrets
- The names and basic information are displayed

6)

As a secret owner
I want to update an existing secret
So that my stored information remains accurate

Acceptance Criteria
- The user can change an existing secret
- The changes are saved
- After updating, the current version is displayed

7)

As a secret owner
I want to delete a secret
So that I can remove information I no longer need

Acceptance Criteria
- The user can delete a secret
- The deleted secret disappears from the list
- The user receives confirmation of the operation

8)

As a CLI user
I want to work with the system through CLI commands
So that I can automate operations and integrate them into scripts

Acceptance Criteria
- The user can perform basic operations through CLI

9)

As a CLI user
I want the application to validate my input data
So that invalid secrets and configuration errors are prevented

Acceptance Criteria
- Incorrect data is rejected
- The user receives an error message
- Valid data is processed successfully

10)

As a multi-device user 
I want to synchronize my secrets across devices
So that I always have access to the latest version of my data

Acceptance Criteria
- Data is synced between devices
- After syncing, the most current version of the data is available
- The user receives the sync status

11)

As a multi-device user
I want to access my secrets from multiple devices
So that I can work from any trusted environment

Acceptance Criteria
- The user can use multiple devices
- Data is available on each trusted device
- Access is maintained after synchronization

12)

As a secret owner
I want to securely share access to secrets with another trusted device
So that multiple devices can work with the same encrypted data

Acceptance Criteria
- The user can send or confirm an access request
- The new device is added to the trust chain
- After confirmation, the device is granted access

13)

As a secret owner
I want to see which devices have access to my secrets
So that I can control access to my data

Acceptance Criteria
- The user can see a list of devices
- Only devices with access are displayed

14)

As a secret owner
I want to revoke access for a trusted device
So that devices I no longer use cannot access my secrets

Acceptance Criteria
- The user can remove the device from trusted devices
- The device loses access to data
- The changes are reflected in the system

15)

As a multi-device user
I want to know whether my last synchronization was successful
So that I can be sure my data is up to date

Acceptance Criteria
- The user can see the time of the last synchronization
- The user is notified of synchronization errors

16)

As an authenticated user
I want to view information about my secrets and requests
So that I can monitor my account activity

Acceptance Criteria
- The user can see their secrets and requests
- The information is displayed correctly
- Data is updated after changes

17)

As a secret owner
I want to search secrets by name
So that I can quickly find the information I need

Acceptance Criteria
- Users can search for secrets by name
- Search results are displayed correctly

18)

As a secret owner
I want to organize my secrets by type
So that I can manage different kinds of sensitive information more efficiently

Acceptance Criteria
- The user can view secrets by category
- Secret types are displayed correctly
- Secrets can be conveniently filtered by type

19)

As a secret owner
I want to view the history of changes to a secret
So that I can understand when and how it was modified

Acceptance Criteria
- The user can view the change history
- The date is displayed for each change

20)

As a security-conscious user
I want to export my encrypted data
So that I can create backups of my secrets

Acceptance Criteria
- The user can export their data
- Exported data is saved to a file

21)

As a security-conscious user
I want to restore my encrypted data from a backup
So that I can recover my secrets if I lose a device

Acceptance Criteria
- The user can download the backup
- The data is successfully restored
- After restoration, the data is available to the user

22)

As an authenticated user
I want to see statistics about my secrets and devices
So that I can monitor my account activity

Acceptance Criteria
- The user can see statistics for secrets
- The user can see statistics for devices
