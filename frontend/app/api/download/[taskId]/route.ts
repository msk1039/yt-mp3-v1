import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await context.params;
    
    if (!taskId) {
      return NextResponse.json(
        { error: 'Task ID is required' },
        { status: 400 }
      );
    }

    // Forward the request to the backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/download/${taskId}`, {
      method: 'GET',
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error('Backend error:', errorText);
      return NextResponse.json(
        { error: 'File not found or download failed', details: errorText },
        { status: backendResponse.status }
      );
    }

    // Get the file stream from backend
    const fileBuffer = await backendResponse.arrayBuffer();
    const contentType = backendResponse.headers.get('content-type') || 'audio/mpeg';
    const filename = backendResponse.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') || `${taskId}.mp3`;

    // Return the file with proper headers
    return new Response(fileBuffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Content-Length': fileBuffer.byteLength.toString(),
      },
    });
    
  } catch (error) {
    console.error('File download error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
