// Small, shared building blocks for the loading/error states every
// data-fetching page needs, so each page doesn't reinvent them.

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <p className="py-8 text-center text-sm text-muted">{label}</p>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      Could not reach the OpsPilot API: {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-6 text-center text-sm text-muted">{message}</p>;
}
