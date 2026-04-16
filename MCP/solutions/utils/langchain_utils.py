"""
LangChain utilities for resume processing
"""

import re

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS

# Initialize LangChain components
def init_langchain_components(api_key, llm_model="gpt-4o-mini", embedding_model="text-embedding-3-small"):
    """Initialize LangChain components.
    
    Args:
        api_key: OpenAI API key
        llm_model: OpenAI chat model
        embedding_model: OpenAI embedding model
        
    Returns:
        tuple: (embeddings, llm) or (None, None) if error
    """
    if not api_key:
        return None, None

    try:
        embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
        llm = ChatOpenAI(temperature=0, model=llm_model, api_key=api_key)
        return embeddings, llm
    except Exception:
        return None, None

def prepare_resume_documents(resume_text, filename):
    """
    Split resume text into chunks and wrap them as LangChain Document objects.
    
    Args:
        resume_text: Raw resume text
        filename: Name of the resume file
    
    Returns:
        dict: Contains original text and chunked Document list
    """
    # Step 1: Chunk the resume
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(resume_text)

    # Step 2: Wrap each chunk in a Document with metadata
    documents = [
        Document(page_content=chunk, metadata={"source": filename, "chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    return {
        "text": resume_text,
        "chunks": documents
    }

def normalize_vector_score(distance):
    """Convert FAISS distance into an easy-to-read relevance score."""
    try:
        distance = float(distance)
    except (TypeError, ValueError):
        return 0.0

    if distance < 0:
        distance = 0

    return 1 / (1 + distance)

def find_relevant_sections(processed_resume, job_description, embeddings):
    """
    Use FAISS vector store to find top 3 resume chunks most relevant to a job description.
    
    Args:
        processed_resume: Output of process_resume_with_langchain (includes chunks)
        job_description: Job description string
        embeddings: OpenAI embeddings object
    
    Returns:
        List of (chunk_text, similarity_score) tuples
    """
    if not embeddings:
        return []

    try:
        # Build FAISS index from processed chunks
        vectorstore = FAISS.from_documents(processed_resume["chunks"], embeddings)

        # Perform semantic search
        results = vectorstore.similarity_search_with_score(job_description, k=3)

        # Return list of (text, score)
        return [(doc.page_content, normalize_vector_score(score)) for doc, score in results]
    except Exception:
        return []


def extract_skills_with_langchain(resume_text, llm):
    """Extract skills from resume text using LangChain.
    
    Args:
        resume_text: Resume text content
        llm: LangChain language model
        
    Returns:
        str: Extracted skills or error message
    """
    if not llm:
        return "LangChain LLM not available for skill extraction."
    
    try:
        # Create a skill extraction chain
        prompt = PromptTemplate.from_template(
            """
            Extract the skills from the following resume. 
            Organize them into categories like:
            - Technical Skills
            - Soft Skills
            - Languages
            - Tools & Platforms
            
            Resume:
            {resume_text}
            
            Extracted Skills:
            """
        )
        
        chain = prompt | llm | StrOutputParser()
        
        # Run the chain
        skills = chain.invoke({"resume_text": resume_text})
        return skills
        
    except Exception as e:
        return f"Error extracting skills: {str(e)}"

def assess_resume_for_job(resume_text, job_description, llm):
    """Assess how well a resume matches a job description.
    
    Args:
        resume_text: Resume text content
        job_description: Job description text
        llm: LangChain language model
        
    Returns:
        str: Assessment or error message
    """
    if not llm:
        return "LangChain LLM not available for resume assessment."
    
    try:
        # Create an assessment chain
        prompt = PromptTemplate.from_template(
            """
            You are a skilled recruiter. Evaluate how well the following resume matches the job description.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Provide an assessment with the following sections:
            1. Match Score: give a single integer from 0 to 100
            2. Matching Skills & Qualifications
            3. Missing Skills & Qualifications
            4. Overall Assessment
            5. Hiring Recommendation
            """
        )
        
        chain = prompt | llm | StrOutputParser()
        
        # Run the chain
        assessment = chain.invoke({
            "resume_text": resume_text,
            "job_description": job_description
        })
        return assessment
        
    except Exception as e:
        return f"Error assessing resume: {str(e)}"

def extract_match_score(assessment_text):
    """Extract a numeric match score from an assessment."""
    if not assessment_text:
        return None

    patterns = [
        r"Match Score\s*[:\-]\s*(\d{1,3})",
        r"Match Score\s*\(\s*0\s*-\s*100\s*\)\s*[:\-]?\s*(\d{1,3})",
        r"(\d{1,3})\s*/\s*100",
    ]

    for pattern in patterns:
        match = re.search(pattern, assessment_text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return max(0, min(score, 100))

    return None

def get_resume_match_analysis(resume_text, filename, job_description, embeddings, llm):
    """Run the full resume-job matching workflow for a single resume."""
    processed_resume = prepare_resume_documents(resume_text, filename)
    relevant_sections = find_relevant_sections(processed_resume, job_description, embeddings)
    assessment = assess_resume_for_job(resume_text, job_description, llm)
    match_score = extract_match_score(assessment)

    return {
        "assessment": assessment,
        "relevant_sections": relevant_sections,
        "match_score": match_score,
    }

def generate_interview_pack_with_langchain(resume_text, job_description, llm):
    """Generate a role-specific interview pack from a resume."""
    if not llm:
        return "LangChain LLM not available for interview pack generation."

    try:
        prompt = PromptTemplate.from_template(
            """
            You are a hiring manager preparing for an interview.

            Resume:
            {resume_text}

            Job Description:
            {job_description}

            Create an interview pack with the following sections:
            1. Candidate Snapshot
            2. Five Technical Questions
            3. Three Behavioral Questions
            4. Two Resume Deep-Dive Questions
            5. Evaluation Signals

            Keep the questions specific to the candidate's background and the role.
            """
        )

        chain = prompt | llm | StrOutputParser()
        return chain.invoke({
            "resume_text": resume_text,
            "job_description": job_description,
        })
    except Exception as e:
        return f"Error generating interview pack: {str(e)}"

def redact_personal_details(resume_text):
    """Redact common personal identifiers before blind screening."""
    redacted_text = resume_text

    redacted_text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL REDACTED]",
        redacted_text,
    )
    redacted_text = re.sub(
        r"(\+?\d[\d\-\(\)\s]{7,}\d)",
        "[PHONE REDACTED]",
        redacted_text,
    )
    redacted_text = re.sub(
        r"https?://(www\.)?linkedin\.com/[^\s]+",
        "[LINKEDIN REDACTED]",
        redacted_text,
        flags=re.IGNORECASE,
    )
    redacted_text = re.sub(
        r"https?://(www\.)?github\.com/[^\s]+",
        "[GITHUB REDACTED]",
        redacted_text,
        flags=re.IGNORECASE,
    )
    redacted_text = re.sub(
        r"https?://[^\s]+",
        "[URL REDACTED]",
        redacted_text,
        flags=re.IGNORECASE,
    )

    return redacted_text

def blind_screen_resume_with_langchain(resume_text, llm):
    """Create a blind-screening version of a resume."""
    if not llm:
        return "LangChain LLM not available for blind screening."

    try:
        prompt = PromptTemplate.from_template(
            """
            You are helping a recruiter perform a blind screening review.

            Redacted Resume:
            {resume_text}

            Create a response with the following sections:
            1. Anonymized Candidate Summary
            2. Core Skills Snapshot
            3. Experience Highlights
            4. Potential Concerns or Gaps
            5. Blind Screening Recommendation
            6. Redacted Resume

            Do not reintroduce personal details such as names, contact information, or profile links.
            """
        )

        chain = prompt | llm | StrOutputParser()
        return chain.invoke({
            "resume_text": redact_personal_details(resume_text),
        })
    except Exception as e:
        return f"Error blind screening resume: {str(e)}"
