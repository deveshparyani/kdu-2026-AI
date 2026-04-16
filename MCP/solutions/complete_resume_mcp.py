"""
Complete Resume Hiring Assistant MCP Tool

This tool combines basic resume access with LangChain-powered analysis,
shortlisting, interview preparation, and blind screening.
"""

import asyncio
import os
from typing import Annotated

import mcp.server.stdio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
from mcp.types import (
    TextContent,
    Tool,
    INVALID_PARAMS,
)
from pydantic import BaseModel, Field

from utils.resume_utils import read_resume, ensure_dir_exists
from utils.langchain_utils import (
    init_langchain_components,
    extract_skills_with_langchain,
    get_resume_match_analysis,
    generate_interview_pack_with_langchain,
    blind_screen_resume_with_langchain,
)

from dotenv import load_dotenv
load_dotenv()

# Initialize the server
server = Server("resume_hiring_assistant")

# Directories and configuration
RESUME_DIR = os.environ.get("RESUME_DIR", "./assets")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Initialize LangChain components
embeddings, llm = init_langchain_components(
    OPENAI_API_KEY,
    llm_model=OPENAI_MODEL,
    embedding_model=OPENAI_EMBEDDING_MODEL,
)

# Pydantic models for tool inputs
class ReadResume(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]

class ListResumes(BaseModel):
    pass

class ExtractSkills(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]

class MatchResume(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]
    job_description: Annotated[str, Field(description="Job description to match against")]

class ShortlistCandidates(BaseModel):
    job_description: Annotated[str, Field(description="Job description to match against")]
    top_n: Annotated[int, Field(description="Number of top candidates to return", default=3, ge=1, le=20)]

class GenerateInterviewPack(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]
    job_description: Annotated[str, Field(description="Job description to match against")]

class BlindScreenResume(BaseModel):
    file_path: Annotated[str, Field(description="Path to the resume PDF file")]

def get_full_resume_path(file_path):
    """Resolve a resume file path."""
    if file_path.startswith('/'):
        return file_path

    return os.path.join(RESUME_DIR, file_path)

def ensure_resume_file_exists(file_path):
    """Validate that the requested resume exists."""
    full_path = get_full_resume_path(file_path)
    if not os.path.exists(full_path):
        raise McpError(INVALID_PARAMS, f"Resume file not found: {file_path}")

    return full_path

def list_resume_files():
    """List all resume PDFs in the resume directory."""
    if not os.path.exists(RESUME_DIR):
        return []

    return sorted([f for f in os.listdir(RESUME_DIR) if f.lower().endswith('.pdf')])

def truncate_text(text, max_length=400):
    """Trim long text blocks for compact tool responses."""
    if len(text) <= max_length:
        return text

    return text[:max_length].rstrip() + "..."

def format_relevant_sections(relevant_sections, truncate_sections=False):
    """Format relevant section matches for responses."""
    if not relevant_sections:
        return "No high-confidence relevant sections were identified.\n"

    response = ""
    for i, (section, relevance_score) in enumerate(relevant_sections, 1):
        section_text = truncate_text(section) if truncate_sections else section
        response += f"Relevant Section {i} (Relevance: {int(relevance_score * 100)}%):\n{section_text}\n\n"

    return response

# MCP Tool implementation
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_resumes",
            description="List all available resume files",
            inputSchema=ListResumes.model_json_schema(),
        ),
        Tool(
            name="read_resume",
            description="Read and extract text from a resume PDF file",
            inputSchema=ReadResume.model_json_schema(),
        ),
        Tool(
            name="extract_skills",
            description="Extract skills from a resume",
            inputSchema=ExtractSkills.model_json_schema(),
        ),
        Tool(
            name="match_resume",
            description="Match a resume against a job description",
            inputSchema=MatchResume.model_json_schema(),
        ),
        Tool(
            name="shortlist_candidates",
            description="Shortlist top candidates for a job description from all available resumes",
            inputSchema=ShortlistCandidates.model_json_schema(),
        ),
        Tool(
            name="generate_interview_pack",
            description="Generate tailored interview questions for a candidate and job description",
            inputSchema=GenerateInterviewPack.model_json_schema(),
        ),
        Tool(
            name="blind_screen_resume",
            description="Create a blind-screening version of a resume with personal details removed",
            inputSchema=BlindScreenResume.model_json_schema(),
        ),
    ]

@server.call_tool()
async def call_tool(name, arguments):
    if name == "list_resumes":
        try:
            resume_files = list_resume_files()

            if not os.path.exists(RESUME_DIR):
                return [TextContent(type="text", text=f"Resume directory {RESUME_DIR} does not exist")]

            if not resume_files:
                return [TextContent(type="text", text="No resume files found in the directory")]

            response = f"Found {len(resume_files)} resume files:\n\n"
            for i, resume_file in enumerate(resume_files, 1):
                response += f"{i}. {resume_file}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing resumes: {str(e)}")]

    elif name == "read_resume":
        try:
            args = ReadResume(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        ensure_resume_file_exists(args.file_path)

        resume_text = read_resume(args.file_path, RESUME_DIR)
        if not resume_text:
            raise McpError(INVALID_PARAMS, f"Failed to read resume: {args.file_path}")

        response = f"Resume: {args.file_path}\n\n{resume_text}"
        return [TextContent(type="text", text=response)]

    elif name == "extract_skills":
        try:
            args = ExtractSkills(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        ensure_resume_file_exists(args.file_path)

        resume_text = read_resume(args.file_path, RESUME_DIR)
        if not resume_text:
            raise McpError(INVALID_PARAMS, f"Failed to read resume: {args.file_path}")

        skills = extract_skills_with_langchain(resume_text, llm)

        response = f"Skills Extracted from '{args.file_path}':\n\n"
        response += skills

        return [TextContent(type="text", text=response)]

    elif name == "match_resume":
        try:
            args = MatchResume(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        ensure_resume_file_exists(args.file_path)

        resume_text = read_resume(args.file_path, RESUME_DIR)
        if not resume_text:
            raise McpError(INVALID_PARAMS, f"Failed to read resume: {args.file_path}")

        analysis = get_resume_match_analysis(
            resume_text,
            os.path.basename(args.file_path),
            args.job_description,
            embeddings,
            llm,
        )

        response = f"Resume-Job Match Analysis for '{args.file_path}':\n\n"

        if analysis["match_score"] is not None:
            response += f"Match Score: {analysis['match_score']}/100\n\n"

        response += "Most Relevant Resume Sections:\n\n"
        response += format_relevant_sections(analysis["relevant_sections"])
        response += "Full Assessment:\n\n"
        response += analysis["assessment"]

        return [TextContent(type="text", text=response)]

    elif name == "shortlist_candidates":
        try:
            args = ShortlistCandidates(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        resume_files = list_resume_files()
        if not resume_files:
            return [TextContent(type="text", text="No resume files found in the directory")]

        candidate_results = []
        skipped_files = []

        for resume_file in resume_files:
            resume_text = read_resume(resume_file, RESUME_DIR)
            if not resume_text:
                skipped_files.append(resume_file)
                continue

            analysis = get_resume_match_analysis(
                resume_text,
                resume_file,
                args.job_description,
                embeddings,
                llm,
            )

            candidate_results.append({
                "file_path": resume_file,
                "match_score": analysis["match_score"] if analysis["match_score"] is not None else 0,
                "assessment": analysis["assessment"],
                "relevant_sections": analysis["relevant_sections"],
            })

        if not candidate_results:
            return [TextContent(type="text", text="No resumes could be analyzed successfully")]

        ranked_candidates = sorted(
            candidate_results,
            key=lambda candidate: candidate["match_score"],
            reverse=True,
        )

        top_candidates = ranked_candidates[:args.top_n]

        response = f"Shortlist Results for the provided job description:\n\n"
        response += f"Analyzed {len(candidate_results)} resumes and selected the top {len(top_candidates)} candidates.\n\n"

        for i, candidate in enumerate(top_candidates, 1):
            response += f"{i}. {candidate['file_path']}\n"
            response += f"Match Score: {candidate['match_score']}/100\n"
            response += "Top Relevant Resume Evidence:\n"
            response += format_relevant_sections(candidate["relevant_sections"][:2], truncate_sections=True)
            response += "Assessment:\n"
            response += candidate["assessment"]
            response += "\n\n"

        if skipped_files:
            response += "Skipped Files:\n"
            for skipped_file in skipped_files:
                response += f"- {skipped_file}\n"

        return [TextContent(type="text", text=response)]

    elif name == "generate_interview_pack":
        try:
            args = GenerateInterviewPack(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        ensure_resume_file_exists(args.file_path)

        resume_text = read_resume(args.file_path, RESUME_DIR)
        if not resume_text:
            raise McpError(INVALID_PARAMS, f"Failed to read resume: {args.file_path}")

        interview_pack = generate_interview_pack_with_langchain(
            resume_text,
            args.job_description,
            llm,
        )

        response = f"Interview Pack for '{args.file_path}':\n\n"
        response += interview_pack

        return [TextContent(type="text", text=response)]

    elif name == "blind_screen_resume":
        try:
            args = BlindScreenResume(**arguments)
        except ValueError as e:
            raise McpError(INVALID_PARAMS, str(e))

        ensure_resume_file_exists(args.file_path)

        resume_text = read_resume(args.file_path, RESUME_DIR)
        if not resume_text:
            raise McpError(INVALID_PARAMS, f"Failed to read resume: {args.file_path}")

        blind_screened_resume = blind_screen_resume_with_langchain(resume_text, llm)

        response = f"Blind Screening Review for '{args.file_path}':\n\n"
        response += blind_screened_resume

        return [TextContent(type="text", text=response)]

    else:
        raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")

async def main():
    """Main entry point for the MCP server."""
    try:
        ensure_dir_exists(RESUME_DIR)

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="resume_hiring_assistant",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        raise

if __name__ == "__main__":
    asyncio.run(main())
