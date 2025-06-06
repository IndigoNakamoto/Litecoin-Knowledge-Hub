# Milestone 5: MVP Feature 2 Implementation (Transaction & Block Explorer)

## Description
This milestone focuses on implementing the transaction and block explorer feature. This involves integrating the RAG system with Litecoin blockchain explorers or direct node APIs to retrieve and display detailed information about transactions and blocks. This will require robust data parsing and formatting to present complex blockchain data in an understandable way.

## Key Tasks
*   Research and select reliable Litecoin blockchain explorer APIs or consider direct node interaction.
*   Implement backend logic to fetch transaction details by ID (status, confirmations, fees).
*   Implement backend logic to fetch block information by height (timestamp, included transactions).
*   Integrate fetched blockchain data into the RAG pipeline for contextual answers.
*   Develop frontend components to display transaction and block information clearly.
*   Implement input validation for transaction IDs and block heights.

## Estimated Time
50 hours

## Dependencies
*   Completed: Milestone 3 (Core RAG Pipeline Implementation)
*   Completed: Milestone 4 (Litecoin Basics & FAQ)

## Acceptance Criteria
*   Users can successfully query transaction details using a transaction ID.
*   Users can successfully query block information using a block height.
*   The system accurately retrieves and presents relevant blockchain data.
*   Responses are well-formatted and easy to interpret.
*   Error handling for invalid IDs/heights is robust.
