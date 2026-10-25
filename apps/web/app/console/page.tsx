import Link from "next/link";
import { PRODUCTS } from "../../lib/nexora/catalog";
import { NEXORA_URL } from "../../lib/site";
import { getActiveOrg, listProductStates } from "../../lib/nexora/data";
import { enableProduct } from "./actions";
import { Button, ProductTile, type ProductStatus } from "../../components/ui";

export default async function ConsoleHomePage() {
  const org = await getActiveOrg();
  const states = await listProductStates(org.id);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold leading-[34px] text-nx-text">Your products</h1>
        <p className="mt-1 text-sm text-nx-text-muted">Everything under this organisation shares one account, one bill and one set of API keys.</p>
      </div>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PRODUCTS.map((product) => {
          const state = states.find((s) => s.slug === product.slug);
          const enabled = state?.enabled ?? false;
          const available = state?.available ?? product.status === "live";
          const status: ProductStatus = enabled ? "enabled" : available ? "available" : "soon";
          const href = product.slug === "vigilo" ? "/dashboard" : `${NEXORA_URL}/products/${product.slug}`;
          return (
            <li key={product.slug}>
              <ProductTile
                name={product.name}
                pitch={product.pitch}
                status={status}
                action={
                  enabled ? (
                    <Link
                      href={href}
                      className="inline-flex h-8 items-center rounded-nx-md border border-nx-border-input px-3 text-sm font-semibold text-nx-text hover:bg-nx-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent"
                    >
                      Open
                    </Link>
                  ) : !available ? (
                    <p className="text-xs text-nx-text-muted">
                      Not open yet. <Link href={href} className="text-nx-accent underline underline-offset-2">What is planned</Link>
                    </p>
                  ) : org.role === "owner" || org.role === "admin" ? (
                    <form action={enableProduct}>
                      <input type="hidden" name="org_id" value={org.id} />
                      <input type="hidden" name="product" value={product.slug} />
                      <Button type="submit" size="sm" variant="secondary">
                        Enable {product.name}
                      </Button>
                    </form>
                  ) : (
                    <p className="text-xs text-nx-text-muted">Ask an admin to enable this.</p>
                  )
                }
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
