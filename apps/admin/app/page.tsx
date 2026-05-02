import { publicEnv } from "./env";

export default function Home() {
  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>hello world</h1>
      <p>service: admin</p>
      <p>api base url: {publicEnv.NEXT_PUBLIC_API_BASE_URL}</p>
    </main>
  );
}
