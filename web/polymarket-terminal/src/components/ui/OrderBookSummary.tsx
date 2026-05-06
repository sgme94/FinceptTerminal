import type { OrderBookSnapshot } from "../../api/types";

type OrderBookSummaryProps = {
  book: OrderBookSnapshot;
};

function formatPrice(price: number) {
  return price.toFixed(2);
}

function formatSize(size: number) {
  return size.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export function OrderBookSummary({ book }: OrderBookSummaryProps) {
  const bestBid = book.bids[0];
  const bestAsk = book.asks[0];
  const spread = bestBid && bestAsk ? bestAsk.price - bestBid.price : null;

  return (
    <div className="order-book-summary" aria-label="Order book summary">
      <div>
        <span>Bid</span>
        <strong>{bestBid ? formatPrice(bestBid.price) : "-"}</strong>
        <small>{bestBid ? formatSize(bestBid.size) : "-"}</small>
      </div>
      <div>
        <span>Ask</span>
        <strong>{bestAsk ? formatPrice(bestAsk.price) : "-"}</strong>
        <small>{bestAsk ? formatSize(bestAsk.size) : "-"}</small>
      </div>
      <div>
        <span>Spread</span>
        <strong>{spread === null ? "-" : formatPrice(spread)}</strong>
        <small>{book.source === "mock" ? "mock" : "api"}</small>
      </div>
    </div>
  );
}
