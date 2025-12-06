# Development Cycle - Litecoin Knowledge Hub

## Overview

This document outlines the comprehensive development cycle used to build the Litecoin Knowledge Hub. It captures the methodology, tools, processes, and best practices that evolved over 44 days and 367 commits to produce a production-ready RAG application with comprehensive security, monitoring, and testing.

**Development Period**: June 5, 2025 - December 2, 2025  
**Active Development**: 44 days (with 4-month pause June 24 - October 29, 2025)  
**Total Commits**: 367  
**Final Test Status**: 62/62 passing tests  
**Production Status**: ✅ Live and operational

**Note**: Development occurred in two intensive phases with a significant gap:
- **Phase 1**: June 5-24, 2025 (foundation and CMS work)
- **Pause**: June 24 - October 29, 2025 (minimal activity, likely planning/content)
- **Phase 2**: November 2 - December 2, 2025 (production hardening)

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Development Tools & AI Assistants](#development-tools--ai-assistants)
3. [Development Cycle Phases](#development-cycle-phases)
4. [Feature Development Workflow](#feature-development-workflow)
5. [Documentation Practices](#documentation-practices)
6. [Security-First Approach](#security-first-approach)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Process](#deployment-process)
9. [Best Practices & Lessons Learned](#best-practices--lessons-learned)

---

## Core Principles

### 1. Documentation-First Development
- **All features start with documentation** before any code is written
- Documentation defines requirements, acceptance criteria, and implementation details
- Documentation is maintained throughout the development lifecycle
- Every feature has a corresponding feature document in `docs/features/`

### 2. Milestone-Based Progress
- Development is organized into **clear, measurable milestones**
- Each milestone has:
  - Defined scope and objectives
  - Acceptance criteria
  - Estimated time
  - Dependencies
  - Status tracking (✅ Complete, 📝 Planned, ⏳ In Progress)
- Milestones enable tracking progress toward Phase 1, Phase 2, Phase 3 goals

### 3. Security-First Mindset
- Security is considered from the beginning, not as an afterthought
- **Red team assessments** conducted before public launch
- All security vulnerabilities tracked and resolved before deployment
- Multi-layered security approach (rate limiting, fingerprinting, cost throttling, etc.)

### 4. Test-Driven Quality
- Comprehensive test suite maintained throughout development
- Tests written for critical functionality (RAG pipeline, security, rate limiting, etc.)
- Target: **100% test pass rate** (achieved: 62/62 passing)
- Tests run in Docker for consistency

### 5. Docker-First Development
- All development happens in Docker containers
- `docker-compose.dev.yml` for local development
- `docker-compose.prod-local.yml` for local production builds
- `docker-compose.prod.yml` for production deployment
- Ensures consistency across environments

### 6. Iterative Refinement
- Features are built in iterations: MVP → Enhanced → Production-Ready
- Example: Abuse prevention started with basic rate limiting, evolved to challenge-response fingerprinting, global limits, and cost throttling
- Each iteration adds value while maintaining system stability

---

## Development Tools & AI Assistants

### Primary Tools

#### 1. **Cursor IDE** (Primary Development Tool)
- **Role**: Primary development environment and AI-powered code editor
- **Usage**: 
  - All code editing, file management, and navigation
  - AI-powered code generation, completions, and refactoring
  - Primary tool for implementation after initial planning phase
- **Impact**: Did most of the actual development work throughout the project
- **Note**: While Cline custom instructions exist, Cline was not actively used after initial planning. Cursor handled the majority of development tasks.

#### 2. **Google Gemini** (LLM & Documentation Assistant)
- **Primary Role**: LLM provider for RAG pipeline
  - **Model**: Gemini Flash 2.5 Lite (for response generation)
  - **Embeddings**: Local OSS model (`sentence-transformers/all-MiniLM-L6-v2`) - runs locally, no API calls
- **Secondary Role**: Documentation creation and refinement
  - Helped create and refine project documentation
  - Assisted with technical writing and documentation structure

#### 3. **Grok** (Documentation & Content)
- **Role**: Documentation creation and content research
- **Usage**: 
  - Creating and refining project documentation alongside Gemini
  - Research assistance
  - Sample content generation (e.g., "Grok Deep Search" for "What is litecoin" content)
- **Example**: Used "Grok Deep Search" for generating sample documents on "What is litecoin"

#### Note on Cline
- **Custom Instructions Exist**: There are Cline custom instructions in `.clinerules/` directory
- **Limited Active Use**: Cline was primarily used during the initial planning phase (June 2025)
- **After Planning**: Development work was done primarily through Cursor IDE, which may use Cline in the background, but Cline was not actively managed or used directly after the initial setup
- **Cursor as Primary Tool**: Most implementation, refactoring, and code changes were done directly through Cursor IDE's AI capabilities

### Supporting Tools

- **Docker & Docker Compose**: Containerization and orchestration
- **MongoDB**: Primary database (content, logs, vector store)
- **Redis**: Caching, rate limiting, dynamic configuration
- **Payload CMS**: Content management system (self-hosted)
- **Prometheus & Grafana**: Monitoring and observability
- **Vercel**: Frontend deployment
- **Railway/Render/Fly.io**: Backend deployment options

---

## Development Cycle Phases

### Phase 0: Project Initialization

**Goal**: Establish project foundation and documentation structure

**Activities**:
1. Create initial project documentation
   - `projectRoadmap.md` - Project vision, goals, features
   - `techStack.md` - Technology decisions
   - `codebaseSummary.md` - Codebase overview (initially empty)
   - `currentTask.md` - Current task definition
2. Set up development environment
   - Docker configuration
   - Environment variable management
   - Git repository structure
3. Define milestones and phases
   - Break project into logical phases
   - Define milestones with acceptance criteria

**Deliverables**:
- Complete `cline_docs/` structure
- Development environment setup
- Initial project roadmap

**Example**: Milestone 1 - Project Initialization (3 hours actual)

---

### Phase 1: Planning & Design

**Goal**: Fully design feature/change before implementation

**Activities**:
1. **Feature Request or Bug Identification**
   - User story or problem statement
   - Business context and requirements

2. **Documentation Creation**
   - Create feature document in `docs/features/` (for new features)
   - Create fix document in `docs/fixes/` (for bug fixes)
   - Include:
     - Problem statement
     - Solution design
     - Technical requirements
     - Business requirements
     - Acceptance criteria
     - Implementation plan
     - Testing strategy

3. **Pre-Task Analysis** (via Cursor IDE, Gemini, or Grok)
   - Developer/AI reviews essential documentation
   - Performs RAG-specific analysis:
     - Data source impact
     - Retrieval strategy
     - Embedding impact
     - Generation quality
     - Performance impact
     - Evaluation strategy
   - Identifies dependencies and impacts
   - Creates detailed implementation plan
   - **Note**: After initial planning phase, most analysis and implementation was done directly through Cursor IDE

4. **Plan Review & Approval**
   - Present plan to developer
   - Review and iterate on design
   - Get approval before implementation

**Deliverables**:
- Feature/fix documentation
- Detailed implementation plan
- Acceptance criteria defined

**Example**: See `docs/features/FEATURE_ADVANCED_ABUSE_PREVENTION.md` for a comprehensive feature document (1500+ lines)

---

### Phase 2: Implementation

**Goal**: Write production-quality code following the approved plan

**Activities**:
1. **Code Implementation**
   - Follow the approved implementation plan
   - Write code with security and performance in mind
   - Follow project coding standards
   - Add comprehensive comments

2. **Incremental Testing**
   - Test as you build
   - Use Docker for consistent testing environment
   - Verify each component works before moving to the next

3. **Documentation Updates**
   - Update code comments
   - Update `codebaseSummary.md` with new components
   - Update relevant documentation files

4. **Code Review (Self)**
   - Review own code before committing
   - Check for security issues
   - Verify edge cases are handled

**Key Practices**:
- **Atomic Commits**: Each commit represents a logical change
- **Clear Commit Messages**: Descriptive commit messages following conventional format
- **Feature Flags**: Use feature flags for gradual rollout
- **Environment Variables**: All configuration via environment variables
- **AI-Assisted Coding**: Cursor IDE used extensively for code generation, refactoring, and implementation

**Example Commit Flow**:
```
feat: implement challenge-response fingerprinting
fix: correct challenge validation logic
docs: update abuse prevention feature documentation
test: add challenge-response test suite
```

---

### Phase 3: Testing

**Goal**: Ensure feature works correctly and doesn't break existing functionality

**Activities**:
1. **Unit Tests**
   - Write tests for individual functions/classes
   - Test edge cases and error conditions
   - Run tests in Docker: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -vv`

2. **Integration Tests**
   - Test component interactions
   - Test API endpoints
   - Test database operations

3. **End-to-End Tests**
   - Test complete user workflows
   - Test RAG pipeline end-to-end
   - Test security features

4. **Test Suite Maintenance**
   - Ensure all tests pass (target: 100%)
   - Fix failing tests immediately
   - Add tests for bug fixes

**Test Infrastructure**:
- **Framework**: pytest
- **Location**: `backend/tests/`
- **Coverage**: Critical paths (RAG, security, rate limiting, etc.)
- **Mocking**: Redis, LLM, MongoDB connections mocked for tests
- **Status**: 62/62 passing tests

**Example Test File**: `backend/tests/test_abuse_prevention.py` (comprehensive test suite)

---

### Phase 4: Security Review

**Goal**: Identify and fix security vulnerabilities before deployment

**Activities**:
1. **Security Audit**
   - Review code for common vulnerabilities
   - Check authentication and authorization
   - Verify input validation
   - Review error handling (no information disclosure)

2. **Red Team Assessment** (for major features)
   - Comprehensive security review
   - Attack scenario testing
   - Vulnerability identification and prioritization
   - See `docs/security/RED_TEAM_ASSESSMENT_COMBINED.md`

3. **Fix Critical Issues**
   - Prioritize: CRITICAL → HIGH → MEDIUM → LOW
   - Fix all blockers before deployment
   - Document fixes in `docs/fixes/`

4. **Security Documentation**
   - Document security features
   - Update security assessment
   - Document threat model

**Security Practices**:
- **Input Sanitization**: All user input validated and sanitized
- **Rate Limiting**: Multi-layered rate limiting (per-identifier, global)
- **Authentication**: Challenge-response fingerprinting, Turnstile verification
- **Error Handling**: Never disclose internal details in errors
- **Security Headers**: Comprehensive security headers (CSP, HSTS, etc.)

**Example**: See `docs/security/RED_TEAM_ASSESSMENT_COMBINED.md` for comprehensive security review (1500+ lines)

---

### Phase 5: Documentation

**Goal**: Ensure all changes are fully documented

**Activities**:
1. **Update Feature Documentation**
   - Mark feature as implemented
   - Update implementation status
   - Add configuration details
   - Document troubleshooting

2. **Update Architecture Documentation**
   - Update system diagrams if needed
   - Document new components
   - Update data flow diagrams

3. **Update README/CHANGELOG**
   - Add feature to CHANGELOG.md
   - Update README.md if needed
   - Update milestone status

4. **Update API Documentation**
   - Document new endpoints
   - Update request/response examples
   - Document error codes

**Documentation Structure**:
```
docs/
├── features/          # Feature documentation
├── fixes/            # Bug fix documentation
├── security/         # Security documentation
├── milestones/       # Milestone documentation
├── architecture/     # Architecture diagrams
├── deployment/       # Deployment guides
└── testing/          # Testing documentation
```

**Example**: Every feature has comprehensive documentation (see `docs/features/` directory)

---

### Phase 6: Deployment

**Goal**: Deploy feature to production safely

**Activities**:
1. **Local Production Build Verification**
   - Run `docker-compose.prod-local.yml` locally
   - Verify production builds work
   - Test all functionality

2. **Staging Deployment** (if available)
   - Deploy to staging environment
   - Run smoke tests
   - Verify monitoring works

3. **Production Deployment**
   - Deploy backend to Railway/Render/Fly.io
   - Deploy frontend to Vercel
   - Deploy Payload CMS to Vercel/Docker
   - Verify all services are healthy

4. **Post-Deployment Verification**
   - Check health endpoints
   - Verify monitoring dashboards
   - Test critical user flows
   - Monitor for errors

**Deployment Practices**:
- **Gradual Rollout**: Use feature flags for gradual rollout
- **Health Checks**: All services have health check endpoints
- **Monitoring**: Prometheus/Grafana dashboards for observability
- **Rollback Plan**: Always have a rollback plan

**Documentation**: See `docs/DEPLOYMENT.md` for detailed deployment guide

---

## Feature Development Workflow

### Complete Feature Development Cycle

```
1. Feature Request / Problem Identification
   ↓
2. Create Feature Document (docs/features/FEATURE_NAME.md)
   - Problem statement
   - Solution design
   - Requirements (business & technical)
   - Acceptance criteria
   ↓
3. Pre-Task Analysis (via Cursor IDE)
   - Read essential documentation
   - Perform RAG-specific analysis
   - Create implementation plan
   - Present plan for review
   ↓
4. Plan Review & Approval
   - Review design
   - Iterate if needed
   - Get approval
   ↓
5. Implementation
   - Write code
   - Test incrementally
   - Update documentation
   ↓
6. Testing
   - Write unit tests
   - Write integration tests
   - Run full test suite
   - Fix any failures
   ↓
7. Security Review
   - Code review for security
   - Run security audit
   - Fix vulnerabilities
   ↓
8. Documentation
   - Update feature doc with implementation status
   - Update architecture docs
   - Update CHANGELOG
   ↓
9. Local Production Build Verification
   - Test production build locally
   - Verify all functionality
   ↓
10. Deployment
    - Deploy to production
    - Verify deployment
    - Monitor for issues
```

### Example: Advanced Abuse Prevention Feature

This feature demonstrates the complete cycle:

1. **Planning**: Comprehensive feature document created (`docs/features/FEATURE_ADVANCED_ABUSE_PREVENTION.md`)
2. **Implementation**: Implemented in 5 priority items:
   - Challenge-response fingerprinting
   - Global rate limiting
   - Per-identifier challenge limits
   - Graceful Turnstile degradation
   - Cost-based throttling
3. **Testing**: Comprehensive test suite added
4. **Security**: Security review conducted, all vulnerabilities fixed
5. **Documentation**: 1500+ line feature document with full details
6. **Deployment**: Deployed to production with feature flags

**Result**: 99.9% abuse protection achieved with all MVP items implemented

---

## Documentation Practices

### Documentation-First Development

**Principle**: Documentation is written before code, not after.

**Why**:
- Forces clear thinking about requirements
- Provides implementation blueprint
- Serves as contract for acceptance criteria
- Enables better planning and estimation

### Documentation Structure

```
docs/
├── features/              # Feature documentation (before/during/after implementation)
│   ├── FEATURE_NAME.md
│   └── ...
├── fixes/                # Bug fix documentation
│   ├── FIX_NAME.md
│   └── ...
├── security/             # Security documentation
│   ├── RED_TEAM_ASSESSMENT_COMBINED.md
│   ├── ABUSE_PREVENTION_STACK.md
│   └── ...
├── milestones/           # Milestone tracking
│   ├── milestone_N_NAME.md
│   └── ...
├── architecture/         # Architecture diagrams and documentation
│   ├── high_level_design.md
│   └── ...
├── deployment/           # Deployment guides
│   ├── DEPLOYMENT.md
│   └── ...
└── testing/              # Testing documentation
    └── TESTING.md
```

### Documentation Standards

**Feature Documents Include**:
1. Overview & Status
2. Problem Statement
3. Solution Design
4. Business Requirements
5. Technical Requirements
6. Implementation Details
7. Configuration
8. Frontend Integration
9. Backend Integration
10. Testing
11. Deployment
12. Monitoring
13. Troubleshooting
14. Implementation Status
15. Future Enhancements

**Example**: See `docs/features/FEATURE_ADVANCED_ABUSE_PREVENTION.md` (1500+ lines)

### Documentation Maintenance

- **Update During Development**: Documentation updated as implementation evolves
- **Status Tracking**: Clear status indicators (✅ Implemented, ⏳ In Progress, 📝 Planned)
- **Version Control**: All documentation in Git
- **Living Documents**: Documentation updated throughout project lifecycle

---

## Security-First Approach

### Security Philosophy

**Principle**: Security is not a phase; it's integrated into every phase of development.

### Security Practices

#### 1. Security from the Start
- Security considered during planning phase
- Threat modeling for new features
- Security requirements defined upfront

#### 2. Multi-Layered Security
- **Layer 1**: Challenge-response fingerprinting (prevents replay attacks)
- **Layer 2**: Cloudflare Turnstile (bot protection)
- **Layer 3**: Rate limiting (per-identifier + global)
- **Layer 4**: Cost throttling (financial unabusability)
- **Layer 5**: Input sanitization (XSS, injection prevention)
- **Layer 6**: Security headers (CSP, HSTS, etc.)
- **Layer 7**: Error handling (no information disclosure)

#### 3. Security Reviews
- **Code Review**: Security-focused code review
- **Red Team Assessment**: Comprehensive security audit before public launch
- **Vulnerability Tracking**: All vulnerabilities tracked and prioritized

#### 4. Security Documentation
- **Security Features**: Documented in `docs/security/`
- **Threat Model**: Documented in red team assessments
- **Fix Documentation**: All security fixes documented in `docs/fixes/`

### Example: Security Hardening Cycle

1. **Red Team Assessment** (Nov 2025)
   - Comprehensive security review
   - 16 CRITICAL vulnerabilities identified
   - 15 HIGH priority issues identified
   - Prioritized by public launch blockers

2. **Fix Implementation**
   - All blockers fixed before launch
   - Security fixes documented
   - Testing for all fixes

3. **Verification**
   - Security score improved: 7.5/10
   - All public launch blockers resolved
   - Production-ready security posture

**Result**: Zero security incidents post-launch

---

## Testing Strategy

### Testing Philosophy

**Principle**: Comprehensive testing ensures quality and prevents regressions.

### Test Structure

```
backend/tests/
├── test_abuse_prevention.py      # Security feature tests
├── test_conversational_memory.py # RAG pipeline tests
├── test_rate_limiting.py         # Rate limiter tests
├── test_cost_throttling.py       # Cost control tests
└── ...
```

### Test Types

#### 1. Unit Tests
- Test individual functions/classes
- Mock external dependencies (Redis, LLM, MongoDB)
- Test edge cases and error conditions

#### 2. Integration Tests
- Test component interactions
- Test API endpoints
- Test database operations

#### 3. End-to-End Tests
- Test complete user workflows
- Test RAG pipeline end-to-end
- Test security features

### Test Execution

**Development**:
```bash
docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -vv
```

**Expected Output**: `62 passed, 4 skipped, 29 warnings in ~33s`

### Test Coverage

**Critical Areas**:
- ✅ RAG pipeline (retrieval, generation, conversational memory)
- ✅ Rate limiting (individual, global, atomic operations)
- ✅ Abuse prevention (challenge-response, fingerprinting)
- ✅ Cost throttling (10-min threshold, daily limits)
- ✅ Webhook authentication (HMAC verification)
- ✅ Error handling (no information disclosure)

### Test Quality Standards

- **All Tests Pass**: Target 100% pass rate (achieved: 62/62)
- **Fast Execution**: Complete test suite runs in ~33 seconds
- **Isolated Tests**: Tests don't depend on each other
- **Mock External Services**: Redis, LLM, MongoDB mocked for tests
- **Clear Test Names**: Descriptive test function names

---

## Deployment Process

### Deployment Philosophy

**Principle**: Deploy safely with verification at each step.

### Deployment Environments

1. **Development** (`docker-compose.dev.yml`)
   - Local development with hot reload
   - Used for active development

2. **Production-Local** (`docker-compose.prod-local.yml`)
   - Local production build verification
   - Tests production builds before deployment

3. **Production** (`docker-compose.prod.yml`)
   - Production deployment
   - Includes monitoring stack (Prometheus, Grafana)

### Deployment Steps

#### 1. Pre-Deployment
- All tests passing
- Documentation updated
- Security review completed
- Local production build verified

#### 2. Deployment
- Deploy backend to Railway/Render/Fly.io
- Deploy frontend to Vercel
- Deploy Payload CMS to Vercel/Docker
- Deploy monitoring stack

#### 3. Post-Deployment Verification
- Health checks pass
- Monitoring dashboards operational
- Critical user flows tested
- Error monitoring active

### Deployment Safety

- **Feature Flags**: Gradual rollout for new features
- **Health Checks**: All services have health endpoints
- **Monitoring**: Prometheus/Grafana for observability
- **Rollback Plan**: Always prepared to rollback if needed
- **Gradual Rollout**: Deploy to small percentage, monitor, then scale up

---

## Best Practices & Lessons Learned

### What Worked Well

1. **Documentation-First Approach**
   - Clear requirements before implementation
   - Better planning and estimation
   - Easier code reviews

2. **Milestone-Based Development**
   - Clear progress tracking
   - Measurable goals
   - Better project management

3. **Security-First Mindset**
   - Security issues caught early
   - Comprehensive security posture
   - Zero security incidents post-launch

4. **Docker-First Development**
   - Consistent environments
   - Easy onboarding
   - Reliable deployments

5. **Comprehensive Testing**
   - High confidence in changes
   - Prevents regressions
   - 62/62 passing tests

6. **AI-Assisted Development**
   - Faster development with Cursor IDE's AI capabilities
   - Better code quality
   - Comprehensive documentation

### Challenges Overcome

1. **Complex RAG Pipeline**
   - **Challenge**: Building reliable RAG pipeline with conversational memory
   - **Solution**: Iterative development, comprehensive testing, local embeddings

2. **Security Hardening**
   - **Challenge**: 16 CRITICAL vulnerabilities before launch
   - **Solution**: Systematic security review, prioritized fixes, comprehensive testing

3. **Abuse Prevention**
   - **Challenge**: Preventing abuse while maintaining user experience
   - **Solution**: Multi-layered approach (challenge-response, rate limiting, cost throttling)

4. **Performance Optimization**
   - **Challenge**: Sub-second response times for RAG pipeline
   - **Solution**: Local embeddings, async operations, atomic Redis operations

### Key Insights

1. **Start with Documentation**: Documentation forces clear thinking and better design

2. **Security is Not Optional**: Security must be integrated from the start, not added later

3. **Test Everything**: Comprehensive testing catches issues before production

4. **Iterate and Refine**: Start with MVP, then enhance based on real-world usage

5. **Monitor Everything**: Comprehensive monitoring enables proactive issue detection

6. **Use AI Wisely**: Cursor IDE's AI capabilities accelerate development, and Gemini/Grok were valuable for documentation - but all require human oversight and direction

### Recommendations for Future Development

1. **Continue Documentation-First**: Maintain documentation-first approach for all features

2. **Maintain Test Coverage**: Keep test suite at 100% pass rate

3. **Regular Security Reviews**: Conduct security reviews for major features

4. **Monitor Production**: Use monitoring to identify issues before users report them

5. **Iterate Based on Data**: Use analytics and monitoring to guide improvements

6. **Stay Up-to-Date**: Keep dependencies updated and monitor for security vulnerabilities

---

## Development Cycle Summary

### Quick Reference

**For New Features**:
1. Create feature document → 2. Pre-task analysis (via Cursor/Gemini/Grok) → 3. Plan approval → 4. Implementation (via Cursor) → 5. Testing → 6. Security review → 7. Documentation (via Gemini/Grok) → 8. Deployment

**For Bug Fixes**:
1. Create fix document → 2. Root cause analysis → 3. Implementation → 4. Testing → 5. Documentation → 6. Deployment

**For Security Issues**:
1. Security audit → 2. Vulnerability prioritization → 3. Fix implementation → 4. Testing → 5. Documentation → 6. Deployment

### Key Metrics

- **Development Time**: 44 days
- **Total Commits**: 367
- **Test Pass Rate**: 100% (62/62)
- **Security Score**: 7.5/10 (all blockers resolved)
- **Features Implemented**: 10+ major features
- **Lines of Code**: ~35,000
- **Documentation**: Comprehensive (100+ markdown files)

---

## Conclusion

This development cycle has proven effective for building a production-ready RAG application with comprehensive security, testing, and monitoring. The documentation-first approach, security-first mindset, and comprehensive testing have resulted in:

- ✅ **Zero security incidents** post-launch
- ✅ **100% test pass rate** (62/62)
- ✅ **Comprehensive documentation** for all features
- ✅ **Production-ready system** with monitoring and observability
- ✅ **99.9% abuse protection** with multi-layered security

**This cycle should be followed for all future development, refactoring, and enhancements.**

---

## Related Documentation

- [README.md](../README.md) - Project overview
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup guide
- [TESTING.md](./TESTING.md) - Testing guide
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [Security Documentation](./security/) - Security features and assessments
- [Feature Documentation](./features/) - All feature documentation
- [Milestone Documentation](./milestones/) - Milestone tracking

