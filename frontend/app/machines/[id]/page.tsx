import { Suspense } from "react";
import MachineDetail from "./machine-detail";

// The machine id is only known at request time, so the client component that
// reads it is wrapped in Suspense (required with cacheComponents).
export default function MachinePage() {
  return (
    <Suspense fallback={<main className="p-8">Loading machine...</main>}>
      <MachineDetail />
    </Suspense>
  );
}
