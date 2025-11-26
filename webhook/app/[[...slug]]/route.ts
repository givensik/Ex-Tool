import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

async function logRequest(req: NextRequest, params: { slug?: string[] }) {
    const method = req.method;
    const path = '/' + (params.slug?.join('/') || '');

    const headers: Record<string, string> = {};
    req.headers.forEach((value, key) => {
        headers[key] = value;
    });

    const searchParams: Record<string, string> = {};
    req.nextUrl.searchParams.forEach((value, key) => {
        searchParams[key] = value;
    });

    let body: string | null = null;
    try {
        const contentType = req.headers.get('content-type');
        if (contentType?.includes('application/json')) {
            body = JSON.stringify(await req.json());
        } else if (contentType?.includes('application/x-www-form-urlencoded') || contentType?.includes('text/plain')) {
            body = await req.text();
        }
    } catch (e) {
        // Ignore body parsing errors
    }

    const ip = req.headers.get('x-forwarded-for') || req.ip || 'unknown';

    try {
        await prisma.log.create({
            data: {
                method,
                path,
                headers: JSON.stringify(headers),
                queryParams: JSON.stringify(searchParams),
                body,
                ip,
            },
        });
    } catch (e) {
        console.error('Failed to log request:', e);
    }
}

export async function GET(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}

export async function POST(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}

export async function PUT(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}

export async function DELETE(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}

export async function PATCH(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}

export async function OPTIONS(req: NextRequest, { params }: { params: { slug?: string[] } }) {
    await logRequest(req, params);
    return new NextResponse('OK', { status: 200 });
}
