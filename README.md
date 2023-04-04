# qbintegration

###Integration layer for dispatch app. API curently does the following:

1. Fetches Customer Accounts Receivable Open Balances.
2. Inserts Invoice from AU Disaptch app to Quickbooks Online.

This py file can be used to integrate dispatch app directly with quickbooks online. Some of the things it can do are:

*Use OAuth to authenticate a user.
*Store access and refresh tokens to manage expirations of both tokens.
*Pull data from quickbooks online.
