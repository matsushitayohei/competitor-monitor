import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    signIn({ profile }) {
      // Only allow @lifull.com domain
      return profile?.email?.endsWith("@lifull.com") ?? false;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
