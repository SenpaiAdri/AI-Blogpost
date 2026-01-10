import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
    // Only apply to the inputted route
    if (request.nextUrl.pathname.startsWith('/api/generate')) {

        const secret = request.nextUrl.searchParams.get('cron_secret')
        const envSecret = process.env.CRON_SECRET

        // Check if the secret matches
        // Note: We check if envSecret exists to allow dev without secrets if needed, 
        // but in prod it MUST be set.
        if (!envSecret || secret !== envSecret) {
            // Return 404 (Not Found) instead of 401 (Unauthorized)
            // This is "security by obscurity" - attackers won't know the route exists.
            return new NextResponse(null, { status: 404 })
        }
    }

    return NextResponse.next()
}

// Configure which paths this middleware runs on
export const config = {
    matcher: '/api/generate/:path*',
}
