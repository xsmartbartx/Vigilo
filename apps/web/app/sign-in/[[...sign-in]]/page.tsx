import { SignIn } from "@clerk/nextjs";
import { AuthPageHeader } from "../../../components/AuthPageHeader";

export default function SignInPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <AuthPageHeader />
      <SignIn />
    </main>
  );
}
