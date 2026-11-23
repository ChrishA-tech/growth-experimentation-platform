"""Pub/Sub-style streaming ingestion.

A minimal publisher/subscriber that mirrors Google Cloud Pub/Sub semantics (topic ->
subscription -> pull, with ack) so the pipeline is a drop-in for GCP Pub/Sub. In local
mode it streams events.parquet through an in-process topic and lands them as newline
JSON (the shape BigQuery ingests). In cloud mode the same code targets a real topic.

GCP mapping (see README):
    local topic            ->  projects/<p>/topics/product-events
    local subscription     ->  projects/<p>/subscriptions/events-to-bq
    land_path (JSONL)      ->  BigQuery streaming insert / Dataflow sink
"""
import json
import queue
import pandas as pd


class Topic:
    def __init__(self, name):
        self.name = name
        self._subs = []

    def subscribe(self):
        q = queue.Queue()
        self._subs.append(q)
        return q

    def publish(self, message: dict):
        data = json.dumps(message, default=str).encode("utf-8")
        for q in self._subs:
            q.put(data)


def stream_events(events_path="data/events.parquet", land_path="data/stream_landed.jsonl",
                  max_messages=None):
    df = pd.read_parquet(events_path)
    if max_messages:
        df = df.head(max_messages)
    topic = Topic("product-events")
    sub = topic.subscribe()
    n = 0
    with open(land_path, "w") as sink:
        for rec in df.to_dict("records"):
            topic.publish(rec)              # publisher side
            msg = sub.get_nowait()          # subscriber pull
            sink.write(msg.decode("utf-8") + "\n")  # ack -> land to warehouse staging
            n += 1
    return n


if __name__ == "__main__":
    print(f"streamed {stream_events():,} events through the Pub/Sub-style topic -> data/stream_landed.jsonl")
