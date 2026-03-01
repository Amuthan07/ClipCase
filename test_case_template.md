# Test Case Template

## Project Information
- **Project Name:** [Enter Project Name]
- **Module/Feature:** [Enter Module/Feature Name]
- **Date Created:** [Enter Date]
- **Created By:** [Enter Name]

---

## Test Case Details

| Test Case ID | Smoke | Sanity | Regression | E2E | Test Case | Automated | System | User Persona | Functional Area | Pre-condition | Expected Outcome/Response | Actual Outcome/Response |
|--------------|-------|--------|------------|-----|-----------|-----------|--------|--------------|-----------------|---------------|---------------------------|-------------------------|
| TC-001 | ☑ | ☐ | ☑ | ☐ | [Describe the test case] | Yes/No | [System name] | [User type] | [Feature area] | [Pre-conditions] | [Expected result] | [Actual result] |
| TC-002 | ☐ | ☐ | ☑ | ☐ | | | | | | | | |
| TC-003 | ☐ | ☑ | ☑ | ☐ | | | | | | | | |
| TC-004 | ☐ | ☐ | ☑ | ☑ | | | | | | | | |
| TC-005 | ☐ | ☐ | ☐ | ☐ | | | | | | | | |

---

## Example Test Cases

| Test Case ID | Smoke | Sanity | Regression | E2E | Test Case | Automated | System | User Persona | Functional Area | Pre-condition | Expected Outcome/Response | Actual Outcome/Response |
|--------------|-------|--------|------------|-----|-----------|-----------|--------|--------------|-----------------|---------------|---------------------------|-------------------------|
| TC-001 | ☑ | ☐ | ☑ | ☐ | Verify user login with valid credentials | No | Web Portal | Admin User | Authentication | - User account exists<br>- User on login page | User successfully logs in and redirects to dashboard | ✅ Pass - Logged in successfully |
| TC-002 | ☑ | ☐ | ☑ | ☐ | Verify login with invalid password | No | Web Portal | End User | Authentication | - Valid username<br>- User on login page | Error message "Invalid credentials" displayed | ✅ Pass - Error shown as expected |
| TC-003 | ☐ | ☑ | ☑ | ☐ | Verify password reset email | Yes | Email System | End User | Authentication | - Valid user account<br>- Valid email registered | Password reset email sent to user | ❌ Fail - Email not received |
| TC-004 | ☐ | ☐ | ☑ | ☑ | Complete user registration flow | Yes | Web Portal | New User | User Management | - Registration page accessible<br>- Email service active | User account created and verification email sent | ✅ Pass - Full flow completed |

---

## Field Definitions

- **Test Case ID:** Unique identifier for the test case (e.g., TC-001)
- **Smoke:** Check (☑) if this is a smoke test (critical functionality)
- **Sanity:** Check (☑) if this is a sanity test (quick verification after changes)
- **Regression:** Check (☑) if this should be included in regression testing
- **E2E:** Check (☑) if this is an end-to-end test (complete user journey)
- **Test Case:** Description of what is being tested
- **Automated:** Yes/No - Indicates if test is automated
- **System:** The system/application being tested
- **User Persona:** Type of user executing the test (Admin, End User, Guest, etc.)
- **Functional Area:** Module or feature area being tested
- **Pre-condition:** Requirements that must be met before test execution
- **Expected Outcome/Response:** What should happen when test is executed correctly
- **Actual Outcome/Response:** What actually happened during test execution (filled during testing)

---

## Notes
- **Pass Criteria:** Document what constitutes a passing test
- **Test Environment:** [Specify environment - Dev/QA/Staging/Production]
- **Test Data Used:** [Reference to test data if applicable]
- **Additional Comments:** [Any other relevant information]

---

## Test Execution Summary

| Metric | Count |
|--------|-------|
| Total Test Cases | [Number] |
| Passed | [Number] |
| Failed | [Number] |
| Blocked | [Number] |
| Not Executed | [Number] |

**Overall Test Result:** [Pass/Fail]

**Tester Name:** [Enter Name]  
**Execution Date:** [Enter Date]
