import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="grid min-h-full place-items-center px-4 text-center">
      <div>
        <p className="text-sm font-semibold text-primary-600">404</p>
        <h1 className="mt-2 text-2xl font-bold">Page not found</h1>
        <Link to="/" className="mt-6 inline-block text-sm font-medium text-primary-600">
          Back to home
        </Link>
      </div>
    </div>
  );
}
