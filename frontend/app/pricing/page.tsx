import { PricingTable } from "@/components/marketing/PricingTable";
import { PublicShell } from "@/components/marketing/PublicShell";

export const metadata = { title: "Pricing | VoxSlot" };

export default function PricingPage() {
  return (
    <PublicShell>
      <section className="public-rings overflow-hidden px-4 pb-20 pt-20 sm:px-6 sm:pt-24">
        <div className="relative z-10 mx-auto max-w-6xl">
          <div className="text-center">
            <p className="text-sm font-medium text-indigo-300">Plans coming soon</p>
            <h1 className="mx-auto mt-3 max-w-4xl text-4xl font-semibold text-white sm:text-5xl">Choose how VoxSlot will support your business</h1>
            <p className="mx-auto mt-4 max-w-2xl text-lg text-[#929eb5]">Pricing is still being finalized. You can create an early workspace now without selecting a paid plan.</p>
          </div>
          <PricingTable />
        </div>
      </section>
    </PublicShell>
  );
}
