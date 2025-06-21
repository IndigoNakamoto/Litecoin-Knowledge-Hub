# **Current Task: Litecoin Knowledge Hub**

## **Current Sprint/Iteration Goal**

* **Milestone 5: Payload CMS Setup & Integration**

## **High-Priority Initiative: CMS Setup & RAG Integration**

## **Active Task(s):**

* ### **Task ID: CMS-SETUP-001**

  * #### **Name: Setup and Integrate Payload CMS**

  * #### **Detailed Description & Business Context: As per the project roadmap, this task involves establishing Payload CMS as the content foundation for the Litecoin Knowledge Hub. The work includes setting up a self-hosted Payload instance, defining the content schemas (collections) for our knowledge base, and building the integration layer that connects the CMS to our RAG pipeline's content ingestion service. This is a critical step to enable a robust, Foundation-controlled editorial workflow.**

  * #### **Acceptance Criteria:**

    1. A self-hosted Payload CMS instance is successfully deployed and configured with a MongoDB database.  
    2. Payload collections are defined to accurately structure the knowledge base articles.  
    3. Role-based access controls (RBAC) are configured for Foundation editors and community contributors.  
    4. Payload's afterChange hooks are implemented to trigger the Content Sync Service upon publishing content.  
    5. The Content Sync Service successfully fetches and processes content from the Payload CMS API.  
    6. The Embedding Processor correctly parses, chunks, and prepares content from Payload for the vector store.  
    7. End-to-end tests confirm that content published in Payload is successfully ingested into the RAG pipeline.  
    8. Relevant project documents (techStack.md, codebaseSummary.md, README.md) are updated to reflect the final Payload CMS integration architecture.

  * #### **Link to projectRoadmap.md goal(s):**

    * Milestone 5: Payload CMS Setup & Integration

  * #### **Status: In Progress**

  * #### **Estimated Effort: 5-7 days**

  * #### **Priority: Critical**

## **Upcoming Phase 1 Tasks**

* ### **Task ID: MVP-CONTENT-001**

  * #### **Name: Populate and Validate MVP Knowledge Base**

  * #### **Detailed Description & Business Context: This task focuses on populating the newly configured Payload CMS with the complete "Litecoin Basics & FAQ" knowledge base. It also includes running end-to-end validation to ensure the content is correctly ingested, processed, and retrieved by the RAG pipeline, providing accurate answers in the chatbot.**

  * #### **Acceptance Criteria:**

    1. All initial "Litecoin Basics & FAQ" articles are created and published within Payload CMS.  
    2. The Content Sync Service correctly processes all new articles from Payload.  
    3. The RAG pipeline successfully retrieves relevant context from the newly populated knowledge base for a battery of test queries.  
    4. Test queries like "What is Litecoin?" and "How is Litecoin different from Bitcoin?" return accurate, expected answers based on the CMS content.  
    5. No data integrity issues are found between the CMS content and the vector store.

  * #### **Link to projectRoadmap.md goal(s):**

    * Milestone 6: MVP Content Population & Validation

  * #### **Status: To Do**

  * #### **Estimated Effort: 3-4 days**

  * #### **Priority: High**

* ### **Task ID: MVP-DEPLOY-001**

  * #### **Name: MVP Testing, Refinement, and Production Deployment**

  * #### **Detailed Description & Business Context: This is the final task for Phase 1\. It involves conducting comprehensive testing (UI/UX, performance, security), refining the user interface based on internal feedback, and executing the full production deployment of all system components (Frontend, Backend, CMS).**

  * #### **Acceptance Criteria:**

    1. A final round of end-to-end testing is completed and passed.  
    2. Any critical or major bugs discovered during testing are resolved.  
    3. The Next.js frontend is successfully deployed to Vercel.  
    4. The FastAPI backend is successfully deployed to its hosting environment.  
    5. All services (Frontend, Backend, CMS, DB) are correctly configured with production environment variables and are communicating successfully.  
    6. The Litecoin Knowledge Hub is publicly accessible and stable.  
    7. Basic monitoring and logging are confirmed to be operational for all production services.

  * #### **Link to projectRoadmap.md goal(s):**

    * Milestone 7: MVP Testing, Refinement & Deployment

  * #### **Status: To Do**

  * #### **Estimated Effort: 4-6 days**

  * #### **Priority: High**

## **Task Backlog:**

[Full Task Backlog](http://docs.google.com/cline_docs/backlogTasks.md)

## **Recently Completed Tasks:**

[View Task Archive](http://docs.google.com/cline_docs/archive/task_archive.md)