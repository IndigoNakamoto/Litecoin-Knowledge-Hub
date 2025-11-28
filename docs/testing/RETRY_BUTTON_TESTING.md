# Retry Button Testing Guide

This guide explains how to test the retry button functionality for challenge response errors.

## Overview

The retry button appears when a `too_many_challenges` error occurs. It shows a countdown timer and allows users to retry their message after the wait period expires.

## Test Panel

A test panel is available in development mode to simulate different retry scenarios.

### Enabling the Test Panel

1. **Automatic in Development**: The test panel is automatically enabled when `NODE_ENV === 'development'`
2. **Manual Toggle**: Click the "🧪 Show Test" button in the top-right corner
3. **Persistent**: The panel state is saved in localStorage, so it persists across page refreshes

### Using the Test Panel

1. **Open the Test Panel**: Click "🧪 Show Test" in the top-right corner
2. **Configure Test Parameters**:
   - **Test Message**: The message that will appear as the user's question
   - **Retry After (seconds)**: How long the countdown should last (1-300 seconds)
   - **Violation Count**: The violation number to display (1-10)
3. **Run Tests**:
   - Click "Test Retry Button" to create a test message with retry info
   - Use quick test buttons (5s, 30s, 60s) for common scenarios

## Testing Scenarios

### Scenario 1: Short Countdown (5 seconds)

**Purpose**: Test that the countdown works and button enables quickly

**Steps**:
1. Open test panel
2. Set "Retry After" to 5 seconds
3. Click "5s Test" or "Test Retry Button"
4. Verify:
   - User message appears with retry button
   - Button shows "⏱️ Wait 5s" and is disabled
   - Countdown decreases: 5s → 4s → 3s → 2s → 1s → 0s
   - Button changes to "🔄 Retry" and becomes enabled
   - Clicking retry removes error and retries message

### Scenario 2: Medium Countdown (30 seconds)

**Purpose**: Test normal wait time behavior

**Steps**:
1. Open test panel
2. Set "Retry After" to 30 seconds
3. Click "30s Test"
4. Verify:
   - Countdown shows "30s" initially
   - After 20 seconds, shows "10s"
   - Button enables when countdown reaches 0
   - Time format changes appropriately (e.g., "1m 30s" for 90+ seconds)

### Scenario 3: Long Countdown (60+ seconds)

**Purpose**: Test time formatting for longer periods

**Steps**:
1. Open test panel
2. Set "Retry After" to 90 seconds
3. Click "Test Retry Button"
4. Verify:
   - Shows "1m 30s" format
   - Minutes and seconds update correctly
   - Button enables after full countdown

### Scenario 4: Multiple Violations

**Purpose**: Test violation count display

**Steps**:
1. Open test panel
2. Set "Violation Count" to 3
3. Set "Retry After" to 10 seconds
4. Click "Test Retry Button"
5. Verify:
   - Error message shows "(Violation #3)"
   - Retry button appears correctly
   - Countdown works as expected

### Scenario 5: Retry Functionality

**Purpose**: Test that retry actually works

**Steps**:
1. Create a test message with 5-second countdown
2. Wait for countdown to complete (or manually set to 0 for testing)
3. Click "🔄 Retry" button
4. Verify:
   - Error message is removed
   - Original message is retried
   - New challenge is fetched
   - Message is sent successfully

## Real-World Testing

### Triggering Real Errors

To test with actual backend errors:

1. **Multiple Tabs Method**:
   - Open 5-10 browser tabs
   - Rapidly send messages from each tab
   - One tab should eventually get a `too_many_challenges` error
   - Verify retry button appears

2. **Rapid Requests Method**:
   - Open browser DevTools → Network tab
   - Send messages very quickly (one after another)
   - Continue until you hit the rate limit
   - Verify error handling and retry button

3. **Backend Simulation**:
   - Temporarily lower rate limits in backend
   - Make a few requests to trigger the error
   - Verify retry button appears with correct countdown

### Expected Error Response

The backend should return:
```json
{
  "detail": {
    "error": "too_many_challenges",
    "message": "Too many active security challenges. Please wait 46 seconds before trying again.",
    "retry_after_seconds": 46,
    "ban_expires_at": 1764280095,
    "violation_count": 1
  }
}
```

## Testing Checklist

- [ ] Test panel appears in development mode
- [ ] Test panel can be toggled on/off
- [ ] Test message creates user message with retry info
- [ ] Retry button appears below user message
- [ ] Countdown timer shows correct time
- [ ] Countdown decreases every second
- [ ] Button is disabled during countdown
- [ ] Button enables when countdown reaches 0
- [ ] Time formatting works (seconds, minutes)
- [ ] Violation count displays correctly
- [ ] Retry button removes error messages
- [ ] Retry button retries the original message
- [ ] Real errors from backend show retry button
- [ ] Multiple violations show correct count

## Debugging

### Check Retry Info in Console

Add this to see retry info:
```javascript
// In browser console
const messages = document.querySelectorAll('[data-message-id]');
messages.forEach(msg => {
  console.log('Message:', msg);
});
```

### Manual State Inspection

In React DevTools:
1. Find the `Home` component
2. Check `messages` state
3. Look for messages with `retryInfo` property
4. Verify all fields are present

### Common Issues

1. **Button doesn't appear**: Check that `retryInfo` is stored in the message
2. **Countdown doesn't work**: Verify `banExpiresAt` or `retryAfterSeconds` is set
3. **Button doesn't enable**: Check countdown logic in `Message.tsx`
4. **Retry doesn't work**: Verify `handleRetryMessage` is called correctly

## Test Panel Features

- **Customizable Parameters**: Adjust retry time, violation count, and message
- **Quick Test Buttons**: Pre-configured tests for common scenarios
- **Visual Feedback**: Yellow panel clearly indicates test mode
- **Non-Intrusive**: Fixed position, doesn't interfere with normal usage

## Production Considerations

- Test panel is **only available in development mode**
- Can be enabled manually via localStorage: `localStorage.setItem('showRetryTestPanel', 'true')`
- Test panel should be disabled in production builds

