# Architecture & Technical Decisions

## 1. Core Architectural Paradign: Zero-Knowledge & Mono-Repo split
- **Decision**: Implementing a strict **Zero-Knowledge model** inside a unified **mono-repo** codebase, dividing the system into an isolated stateless server component and a stateful client binary.
- **Rationale**: 
    - The server is architected as a "blind" storage orchestrator. It never processes unencrypted private keys or raw payloads. By keeping the cryptographic burden entirely on the client, the backend remains lightweight, scale-ready, and legally/technically resilient against data leaks.\
    - A mono-repo approach ensures tight synchronization of network communication protocols and API contracts. It simplifies localized builds, artifact versioning, and developer experience while enforcing a strict boundary rule: the client application never imports anything from the backend and vice versa.

## 2. Backend API Stack Decisions

### High-Performance Asynchronous Framework: FastAPI
- **Decision**: Selected as the primary presentation layer framework for the server component.
- **Rationale**: It leverages native asynchronous concurrent request processing, delivering high-throughput performance with low latency overhead. Automated serialization and runtime validation of input/output data transfer objects (DTOs) heavily reduce development overhead and eliminate a common vector for data-injection bugs.

### Reactive Data Access: SQLAlchemy (Async) + asyncpg
- **Decision**: Utilizing an asynchronous Object-Relational Mapper coupled with a high-performance, native-protocol driver.
- **Rationale**: This ensures non-blocking database input/output execution paths across the entire service layer. The direct binary protocol mapping handles large-scale binary blocks (BYTEA) and connection pools effectively, preventing worker pool starvation under dense, high-load cryptographic storage operations.

### Core Database: PostgreSQL
- **Decision**: Adopted as the primary relational database system.
- **Rationale**: The architectural requirements dictate strict enterprise compliance, operational atomicity, and native support for advanced binary fields (`BYTEA`) and logical tracking flags (`BOOLEAN`). Furthermore, its capability to handle high-concurrency safe updates (`ON CONFLICT DO UPDATE`) allows for reliable, idempotent distributed registration and atomic version increment logic.

### Separate Database Migration Tooling: dbmate
- **Decision**: Using a dedicated, framework-agnostic lightweight migration runner.
- **Rationale**: Decoupling schema tracking from the application framework runtime ensures clean infrastructure deployments. It forces migrations to be written in native SQL, making them explicit, maintainable, easily testable via continuous integration pipelines, and safe against state corruption caused by application-level code mutations.

### Configuration Management: Dynaconf
- **Decision**: Layered configuration management for different deployment environments.
- **Rationale**: It dynamically isolates settings for development, testing, staging, and production environments without modifying the system logic. It supports secure, dynamic injection of production configuration overrides directly from secret storage solutions or deployment orchestration systems.

### Package and Workspace Tooling: uv
- **Decision**: Utilizing a high-speed, modern workspace compiler and environment runner.
- **Rationale**: This dramatically accelerates deployment assembly pipelines, minimizes artifact container footprints, and ensures reproducible, locked runtime environments across both development and distributed staging servers.

## 3. Client Binary Tooling: Go Language (Golang)
- **Decision**: Designing and building the client CLI entirely using Go.
- **Rationale**:
    - **Static Compilation & Zero Dependencies**: Compiles into a single, statically-linked binary executable. This guarantees immediate out-of-the-box local execution on user nodes without requiring pre-installed runtimes, specific shared libraries, or interpreter management tools.
    - **Cryptographic Capability & Security**: Offers excellent access to low-level cryptographic extensions and multi-platform native compiling. Memory safety features drastically mitigate local side-channel or memory-corruption vulnerabilities common during key management and envelope encryption procedures.
    - **Cross-Compilation**: Enables native compilation for multiple targets (Linux, macOS, Windows across different CPU architectures) from a single deployment script, ensuring seamless distribution for diverse operational environments.

## 4. Client CLI Storage & Configuration Strategy

### Local Relational Storage: SQLite
- **Decision**: Utilizing a local embedded relational database engine for client-state tracking, cryptographic metadata, and the local trust graph.
- **Rationale**: 
    - **Zero-Administration & Single File**: It runs entirely within the CLI process memory space and stores all data in a single, compact local file. This eliminates the need to manage a separate local daemon or server process on the user's machine.
    - **Relational Integrity for Trust Chains**: Tracking local devices, synchronization states, and complex trust graphs (e.g., verifying which local device identity signed which target node) requires a relational model with strict Foreign Key constraints and atomic transactions (ACID). This ensures the local state can never be partially written or corrupted during abrupt application termination.
    - **Secure Binary Storage**: It naturally handles binary large objects (BLOB), which is essential for storing encrypted payload blocks and local keys without requiring brittle text encoding schemes.

### User-Modifiable Settings: YAML Configuration
- **Decision**: Separating application state from user configuration by keeping human-editable parameters in a clear text-based format.
- **Rationale**: 
    - **Separation of Concerns**: Parameters that a user needs to modify (such as backend server endpoints, connection timeouts, log levels, or default profile names) are decoupled from the sensitive application state.
    - **Human-Readable Boundaries**: Storing these preferences in a readable layout prevents users from manually editing or inadvertently corrupting the internal database tables (`SQLite`). This acts as an operational boundary: the database is managed strictly via application logic, while the configuration file remains an exposed user interface.
    