"""Calls a running server end to end and prints what the frontend would receive."""

import os

import httpx

BASE_URL = "http://127.0.0.1:8000"
TOKEN = os.getenv("SMOKE_TOKEN", "").strip()
AUTH = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
QUESTIONS = [
    "Benign breast tumors in adult women",
    "Malignant brain tumors in adults",
    "Malaria treatment in children",
]


# Prints the health summary and how many records the collection holds.
def check_health(client):
    health = client.get("/api/health").json()
    print(
        f"health: {health['status']} v{health['version']} | model {health['model']['status']} "
        f"({health['model']['model_id']}) | records {health['documents']['total']} "
        f"| min relevance {health['retrieval']['min_relevance']}"
    )


# Runs every demo question through /api/search and prints the outcome.
def check_questions(client):
    for question in QUESTIONS:
        result = client.post("/api/search", json={"query": question}).json()
        print(f"\nquestion: {question}")
        print(f"  status: {result['status']}")
        if result["status"] == "ok":
            print(f"  answer: {result['answer'][:200]}")
            for source in result["sources"]:
                print(
                    f"  source {source['n']}: {source['title'][:60]} | "
                    f"{source['condition_classification']} | {source['patient_group']} | {source['score']}"
                )
            for item in result["excluded"]:
                print(f"  excluded {item['document_id']}: {'; '.join(item['reasons'])}")
        else:
            print(f"  message: {result.get('message')} | {result.get('detail')}")
            for item in result.get("excluded", []):
                print(f"  excluded {item['document_id']}: {'; '.join(item['reasons'])}")


# Prints the document count and the two newest titles, or the expected sign-in refusal.
def check_documents(client):
    response = client.get("/api/documents", headers=AUTH)
    if response.status_code in (401, 403):
        print(f"\ndocuments: sign-in required ({response.status_code}); set SMOKE_TOKEN to list them")
        return
    documents = response.json()["documents"]
    print(f"\ndocuments: {len(documents)}")
    for document in documents[:2]:
        print(
            f"  {document['document_id']}: {document['title'][:60]} | "
            f"{document['condition_classification']} | {document['patient_group']}"
        )


# Runs the whole smoke test when called with "python -m scripts.smoke_test".
def main():
    with httpx.Client(base_url=BASE_URL, timeout=180.0) as client:
        check_health(client)
        check_documents(client)
        check_questions(client)
    print("\nhistory items:", len(httpx.get(BASE_URL + "/api/history", headers=AUTH, timeout=30.0).json()["items"]))


# Starts the script when it is executed directly.
if __name__ == "__main__":
    main()

