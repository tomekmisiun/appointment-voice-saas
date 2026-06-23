import { redirect } from "next/navigation";

export default function RootPage() {
  // The dashboard layout itself enforces auth and bounces to /login when
  // there's no valid session — no need to duplicate that check here.
  redirect("/dashboard");
}
