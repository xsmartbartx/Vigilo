import Link from "next/link";
import { Footer } from "../../components/Footer";
import { Header } from "../../components/Header";
import { SignOutOnMount } from "../../components/SignOutOnMount";
import { Card } from "../../components/ui";

export const metadata = { title: "Account deleted", robots: { index: false } };

export default function AccountDeletedPage() {
  return (
    <>
      <SignOutOnMount />
      <Header />
      <main className="mx-auto w-full max-w-md flex-1 px-4 py-16">
        <Card className="space-y-3">
          <h1 className="text-xl font-semibold text-nx-text">Your account has been deleted</h1>
          <p className="text-sm text-nx-text-muted">
            Your data is gone and you have been signed out. You can come back and start again with a
            new account whenever you like.
          </p>
          <Link href="/" className="text-sm text-nx-link underline underline-offset-2">
            Back to the home page
          </Link>
        </Card>
      </main>
      <Footer />
    </>
  );
}
