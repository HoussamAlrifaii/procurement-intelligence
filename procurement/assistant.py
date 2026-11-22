"""AI assistant for small businesses looking at public tenders.

The LLM turns a company or tender description into tool calls, our tools return
the numbers (SQL and the two models), and the LLM writes the answer from them.

Usage:
    python -m procurement.assistant "We are an IT company in Poland installing networks, EUR 50k-500k"
    python -m procurement.assistant --trace "..."    # also show the tool calls
"""
import argparse
import json

import duckdb

from procurement import config
from procurement.tools import TOOL_SCHEMAS, cpv_division_names, run_tool


def system_prompt():
    divisions = "\n".join(f"{code}: {name}" for code, name in cpv_division_names().items())
    return f"""You help small and medium-sized companies understand EU public procurement markets.

How to work:
1. Translate the user's description into CPV codes, a two-letter country code if one is mentioned,
   and a value range if one is given. CPV codes are hierarchical: 2 digits = division (listed below),
   3 = group, 4 = class, 5 = category. Use the most specific codes you are sure of, and the division
   when unsure. Buyers code similar work differently, so search related codes together in one call
   (installation, equipment and service codes). Examples: network cabling -> 45314 (telecommunications
   installation), 3242 (network equipment) and 72 (IT services); software -> 48 and 72; office cleaning -> 9091;
   medical consumables -> 331; pharmaceuticals -> 336; road works -> 45233; catering -> 5552.
   estimate_price and single_bid_risk need a code of at least three digits.
   CPV divisions:
{divisions}
2. For a company or market question, call search_market. For a specific planned tender, call
   estimate_price and single_bid_risk. Call several tools when that helps.
3. If a tool returns an error, fix the arguments and call it again.

How to answer:
- Use only numbers that appear in tool results, written exactly as the tools give them. Never estimate,
  round, combine or derive new figures or ranges from them. If the tools did not return something,
  say it is not available.
- Say which CPV groups and country you searched, and that data covers EU contract awards {config.ASSISTANT_FIRST_YEAR}-{config.ASSISTANT_LAST_YEAR}.
- Be concise: a short summary, then bullet points, then one practical suggestion.
- Single-bid risk and price ranges are indicators, not guarantees or accusations."""


def ask(question, llm, connection, max_steps=config.ASSISTANT_MAX_STEPS):
    """Answer one question. Returns the answer and every tool call made, for display and evaluation."""
    messages = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": question},
    ]
    tool_log = []

    for _ in range(max_steps):
        reply = llm(messages, TOOL_SCHEMAS)
        if not reply.tool_calls:
            return {"answer": reply.content, "tool_calls": tool_log}

        # Record the LLM's request, run each tool, and send the results back.
        messages.append({
            "role": "assistant",
            "content": reply.content,
            "tool_calls": [
                {"id": call.id, "type": "function",
                 "function": {"name": call.name, "arguments": json.dumps(call.arguments)}}
                for call in reply.tool_calls
            ],
        })
        for call in reply.tool_calls:
            result = run_tool(connection, call.name, call.arguments)
            tool_log.append({"name": call.name, "arguments": call.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})

    return {"answer": "Sorry, I could not finish this request. Please rephrase it.", "tool_calls": tool_log}


def main():
    from procurement.llm import LLM

    parser = argparse.ArgumentParser(description="Ask the procurement assistant a question.")
    parser.add_argument("question")
    parser.add_argument("--trace", action="store_true", help="show the tool calls and their results")
    arguments = parser.parse_args()

    with duckdb.connect(str(config.DATABASE_PATH), read_only=True) as connection:
        result = ask(arguments.question, LLM(), connection)

    if arguments.trace:
        for call in result["tool_calls"]:
            print(f"\n[{call['name']}] {json.dumps(call['arguments'], ensure_ascii=False)}")
            print(json.dumps(call["result"], indent=2, ensure_ascii=False, default=str))
        print("\n" + "-" * 70)
    print(result["answer"])


if __name__ == "__main__":
    main()
