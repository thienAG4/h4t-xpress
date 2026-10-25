// DonePage - D-14 (Figma "Successful"): the order status was saved; back to the route

import { Link, useParams, useSearchParams } from "react-router";
import { useDriverOrder } from "../hooks";

export function DonePage() {
  const { orderId = "" } = useParams();
  const [params] = useSearchParams();
  const order = useDriverOrder(orderId);
  const failed = params.get("result") === "failed";
  const code = order.data?.waybill_code ?? "";

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 text-center">
      <p
        className={
          "flex size-20 items-center justify-center rounded-full border-4 font-display text-xl font-bold " +
          (failed ? "border-warning-500 text-warning-700" : "border-success-500 text-success-700")
        }
      >
        {failed ? "Saved" : "Done"}
      </p>
      <h1 className="text-xl font-bold">{failed ? "Attempt recorded" : "Successful"}</h1>
      <p className="max-w-xs text-sm text-neutral-600">
        {failed
          ? `Order ${code} was marked as undelivered. The customer and the shop have been informed.`
          : `Your order ${code} status has been updated successfully.`}
      </p>
      <Link
        to="/driver/route"
        className="mt-4 inline-flex h-[50px] w-full max-w-xs items-center justify-center rounded-button bg-primary-600 font-display font-bold text-white"
      >
        BACK
      </Link>
    </div>
  );
}
