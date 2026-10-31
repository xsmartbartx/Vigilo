import Link from "next/link";
import { SignUp } from "@clerk/nextjs";
import { AuthPageHeader } from "../../../components/AuthPageHeader";

export default function SignUpPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <AuthPageHeader />
      <SignUp />
      <p className="max-w-xs text-center text-xs text-black/60 dark:text-white/60">
        By creating an account you agree to the{" "}
        <Link href="/terms" className="underline underline-offset-2">
          Terms of Service
        </Link>{" "}
        and acknowledge the{" "}
        <Link href="/privacy" className="underline underline-offset-2">
          Privacy Policy
        </Link>
        .
      </p>
    </main>
  );
}
