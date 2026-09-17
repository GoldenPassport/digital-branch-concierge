"""Commit the concierge system prompt to LangSmith Prompts as `concierge-system`.

    uv run python scripts/push_prompt.py --tag staging "Describe the change"

Promote a commit to production in the LangSmith UI (Prompts > concierge-system)
after its experiment has passed; the running concierge picks up the commit
tagged `production` within five minutes.
"""

import argparse

from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langsmith import Client  # noqa: E402

from concierge.prompts import PROMPT_NAME, SYSTEM_PROMPT  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("description")
    parser.add_argument("--tag", action="append", default=[])
    args = parser.parse_args()
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("placeholder", "{messages}")])
    url = Client().push_prompt(
        PROMPT_NAME,
        object=prompt,
        description="System prompt for the digital branch concierge (LangGraph build).",
        commit_description=args.description,
        commit_tags=args.tag or None,
    )
    print(url)


if __name__ == "__main__":
    main()
