'use client';

import { useState, useCallback, useEffect } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { downloadHistoryUtils, type DownloadHistoryItem } from "@/lib/download-history";
import { 
    Loader2, 
    Download, 
    AlertCircle, 
    CheckCircle, 
    Music, 
    Clock, 
    RefreshCw,
    ExternalLink,
    FileAudio,
    User,
    Calendar,
    HardDrive,
    RotateCcw
} from "lucide-react";

// Task status enum
enum TaskStatus {
    PENDING = 'pending',
    DOWNLOADING = 'downloading',
    CONVERTING = 'converting',
    COMPLETED = 'completed',
    FAILED = 'failed'
}

// Enhanced task interface
interface TaskData {
    taskId: string;
    status: TaskStatus;
    progress: number;
    message: string;
    title?: string;
    channel?: string;
    thumbnail?: string;
    error?: string;
    fileSize?: number;
    fileSizeFormatted?: string;
    downloadUrl?: string;
    downloadCount?: number;
    expiresText?: string;
}

export default function HomePage() {
    const { toast } = useToast();
    
    // Enhanced state management
    const [youtubeUrl, setYoutubeUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [taskData, setTaskData] = useState<TaskData | null>(null);
    const [error, setError] = useState('');
    const [retryCount, setRetryCount] = useState(0);
    const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
    
    // Download history (using localStorage)
    const [downloadHistory, setDownloadHistory] = useState<DownloadHistoryItem[]>([]);
    
    // Load download history on component mount
    useEffect(() => {
        // Remove expired items on load
        downloadHistoryUtils.removeExpiredItems();
        
        // Load history
        const history = downloadHistoryUtils.getHistory();
        setDownloadHistory(history);
    }, []);
    
    // Cleanup polling interval on unmount
    useEffect(() => {
        return () => {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
        };
    }, [pollingInterval]);
    
    // Poll task status
    const pollTaskStatus = async (taskId: string) => {
        try {
            // Maximum number of polling attempts (180 seconds with 3-second intervals)
            const maxAttempts = 60;
            let attempts = 0;
            
            // Create polling interval
            const interval = setInterval(async () => {
                try {
                    // Use Next.js API route instead of direct backend call
                    const response = await fetch(`/api/status/${taskId}`, {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                    });
                    
                    // Check if response is ok
                    if (!response.ok) {
                        throw new Error(`Server returned ${response.status} ${response.statusText}`);
                    }
                    
                    // Parse response data
                    const data = await response.json();
                    
                    // Exit if max attempts reached
                    if (attempts >= maxAttempts) {
                        clearInterval(interval);
                        setError('Operation timed out. Please try again.');
                        setIsLoading(false);
                        setPollingInterval(null);
                        return;
                    }
                    
                    // Create updated task data
                    const updatedTaskData: TaskData = {
                        taskId: taskId,
                        status: data.status as TaskStatus,
                        progress: data.progress || 0,
                        message: data.message || 'Processing...',
                        title: data.title || taskData?.title,
                        channel: data.channel || taskData?.channel,
                        thumbnail: data.thumbnail || taskData?.thumbnail,
                        error: data.error,
                        fileSize: data.fileSize,
                        fileSizeFormatted: data.fileSizeFormatted,
                        downloadUrl: data.status === 'completed' ? `/api/download/${taskId}` : undefined,
                        downloadCount: data.downloadCount || 0,
                        expiresText: data.expiresText
                    };
                    
                    // Update task data
                    setTaskData(updatedTaskData);
                    
                    // Check status
                    if (data.status === 'completed') {
                        // Task completed, show download link
                        clearInterval(interval);
                        setIsLoading(false);
                        setPollingInterval(null);
                        
                        // Add to download history
                        const historyItem: DownloadHistoryItem = {
                            taskId: updatedTaskData.taskId,
                            title: updatedTaskData.title,
                            channel: updatedTaskData.channel,
                            thumbnail: updatedTaskData.thumbnail,
                            fileSizeFormatted: updatedTaskData.fileSizeFormatted,
                            downloadUrl: updatedTaskData.downloadUrl,
                            completedAt: new Date().toISOString(),
                            downloadCount: updatedTaskData.downloadCount || 0
                        };
                        
                        downloadHistoryUtils.addToHistory(historyItem);
                        setDownloadHistory(downloadHistoryUtils.getHistory());
                        
                        // Show success toast
                        toast({
                            title: "Download Ready!",
                            description: `${updatedTaskData.title || 'Your file'} has been converted successfully.`,
                        });
                        
                        return;
                    } else if (data.status === 'failed') {
                        // Task failed
                        clearInterval(interval);
                        setIsLoading(false);
                        setPollingInterval(null);
                        setError(data.error || 'Conversion failed');
                        
                        // Show error toast
                        toast({
                            variant: "destructive",
                            title: "Conversion Failed",
                            description: data.error || 'The conversion process failed. Please try again.',
                        });
                        
                        return;
                    }
                    
                    // Increment attempt counter
                    attempts++;
                } catch (err) {
                    // Handle polling errors
                    console.error('Polling error:', err);
                    
                    // Increment attempt counter and retry
                    attempts++;
                    
                    // Only show error and stop polling if we've reached maximum attempts
                    // or if the error is more than transient
                    if (attempts >= 3) {  // After 3 consecutive failures, show error
                        clearInterval(interval);
                        setIsLoading(false);
                        setPollingInterval(null);
                        setError(err instanceof Error ? 
                            `Status check failed: ${err.message}` : 
                            'Failed to check conversion status. Please try refreshing the page.');
                        
                        // Show error toast
                        toast({
                            variant: "destructive",
                            title: "Connection Error",
                            description: "Failed to check conversion status. Please try again.",
                        });
                    }
                }
            }, 3000); // Poll every 3 seconds
            
            setPollingInterval(interval);
            
        } catch (err) {
            // Handle initial polling setup error
            console.error('Polling setup error:', err);
            setIsLoading(false);
            setError(err instanceof Error ? 
                `Failed to set up status tracking: ${err.message}` : 
                'Failed to check conversion status');
        }
    };

    // Reset states
    const resetStates = () => {
        setError('');
        setTaskData(null);
        setRetryCount(0);
        if (pollingInterval) {
            clearInterval(pollingInterval);
            setPollingInterval(null);
        }
    };

    // Handle form submission
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        // Reset states
        resetStates();
        
        // Validate URL (basic validation)
        if (!youtubeUrl.trim() || 
            !(youtubeUrl.includes('youtube.com') || youtubeUrl.includes('youtu.be'))) {
            setError('Please enter a valid YouTube URL');
            return;
        }
        
        // Set loading state
        setIsLoading(true);
        
        try {
            // Use Next.js API route instead of direct backend call
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: youtubeUrl }),
            }).catch(error => {
                throw new Error('Failed to connect to the conversion service. Please check if the server is running.');
            });
            
            // Parse response
            const data = await response.json().catch(error => {
                throw new Error('Invalid response from server');
            });
            
            // Handle API errors
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to process request');
            }
            
            // Create initial task data
            const initialTaskData: TaskData = {
                taskId: data.taskId,
                status: TaskStatus.PENDING,
                progress: 0,
                message: 'Starting conversion...',
                downloadCount: 0
            };
            
            setTaskData(initialTaskData);
            
            // Begin polling for status
            await pollTaskStatus(data.taskId);
            
        } catch (err) {
            console.error('Error:', err);
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
            setIsLoading(false);
            
            // Show error toast
            toast({
                variant: "destructive",
                title: "Request Failed",
                description: err instanceof Error ? err.message : 'An unknown error occurred',
            });
        }
    };

    // Handle retry
    const handleRetry = () => {
        setRetryCount(prev => prev + 1);
        handleSubmit({ preventDefault: () => {} } as React.FormEvent);
    };

    // Handle downloading
    const handleDownload = () => {
        if (!taskData?.downloadUrl) return;
        
        // Update download count in both state and localStorage
        setTaskData(prev => prev ? {
            ...prev,
            downloadCount: (prev.downloadCount || 0) + 1
        } : null);
        
        if (taskData?.taskId) {
            downloadHistoryUtils.updateDownloadCount(taskData.taskId, (taskData.downloadCount || 0) + 1);
            setDownloadHistory(downloadHistoryUtils.getHistory());
        }
        
        // Create an invisible iframe to handle the download without navigation
        // This prevents CORS issues with the download
        const downloadFrame = document.createElement('iframe');
        downloadFrame.style.display = 'none';
        document.body.appendChild(downloadFrame);
        
        try {
            // Set source to download URL
            downloadFrame.src = taskData.downloadUrl;
            
            // Remove the iframe after a delay
            setTimeout(() => {
                try {
                    document.body.removeChild(downloadFrame);
                } catch (e) {
                    console.error("Error removing download frame:", e);
                }
            }, 5000);
        } catch (err) {
            console.error("Error initiating download:", err);
            // Fallback to direct navigation if iframe approach fails
            window.open(taskData.downloadUrl, '_blank');
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-2xl">
            <Card className="w-full">
                <CardHeader>
                    <CardTitle className="text-2xl font-bold text-center">
                        YouTube to MP3 Converter
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label htmlFor="youtubeUrl" className="text-sm font-medium">
                                Enter YouTube URL
                            </label>
                            <Input
                                id="youtubeUrl"
                                type="url"
                                placeholder="https://www.youtube.com/watch?v=..."
                                value={youtubeUrl}
                                onChange={(e) => setYoutubeUrl(e.target.value)}
                                disabled={isLoading}
                                className="w-full"
                            />
                        </div>
                        
                        <Button 
                            type="submit" 
                            className="w-full" 
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Processing...
                                </>
                            ) : (
                                "Convert to MP3"
                            )}
                        </Button>
                    </form>
                    
                    {/* Loading State with Progress */}
                    {isLoading && taskData && (
                        <div className="mt-4 space-y-4">
                            {taskData.title && taskData.thumbnail && (
                                <Card className="p-3">
                                    <div className="flex items-center space-x-3">
                                        <img 
                                            src={taskData.thumbnail} 
                                            alt={taskData.title} 
                                            className="h-16 w-28 object-cover rounded"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-sm truncate">{taskData.title}</h3>
                                            {taskData.channel && (
                                                <p className="text-xs text-gray-600 flex items-center mt-1">
                                                    <User className="h-3 w-3 mr-1" />
                                                    {taskData.channel}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </Card>
                            )}
                            
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Badge variant={
                                        taskData.status === TaskStatus.DOWNLOADING ? "default" :
                                        taskData.status === TaskStatus.CONVERTING ? "secondary" :
                                        "outline"
                                    }>
                                        {taskData.status === TaskStatus.DOWNLOADING && "Downloading"}
                                        {taskData.status === TaskStatus.CONVERTING && "Converting"}
                                        {taskData.status === TaskStatus.PENDING && "Pending"}
                                    </Badge>
                                    <span className="text-sm text-gray-500">{taskData.progress}%</span>
                                </div>
                                <Progress value={taskData.progress} className="w-full" />
                                <p className="text-sm text-gray-600 text-center">
                                    {taskData.message}
                                </p>
                            </div>
                        </div>
                    )}
                    
                    {/* Error State */}
                    {error && (
                        <div className="mt-4 space-y-3">
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                            {retryCount < 3 && (
                                <Button 
                                    variant="outline" 
                                    onClick={handleRetry}
                                    className="w-full"
                                >
                                    <RefreshCw className="mr-2 h-4 w-4" />
                                    Retry ({retryCount}/3)
                                </Button>
                            )}
                        </div>
                    )}
                    
                    {/* Download Ready State */}
                    {taskData?.status === TaskStatus.COMPLETED && taskData.downloadUrl && (
                        <div className="mt-4">
                            <Card className="p-4 bg-green-50 border-green-200">
                                {taskData.title && taskData.thumbnail && (
                                    <div className="flex items-center space-x-3 mb-4">
                                        <img 
                                            src={taskData.thumbnail} 
                                            alt={taskData.title} 
                                            className="h-16 w-28 object-cover rounded"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-sm truncate">{taskData.title}</h3>
                                            {taskData.channel && (
                                                <p className="text-xs text-gray-600 flex items-center mt-1">
                                                    <User className="h-3 w-3 mr-1" />
                                                    {taskData.channel}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )}
                                
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center">
                                            <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                                            <span className="text-sm font-medium">Ready for Download</span>
                                        </div>
                                        {taskData.fileSizeFormatted && (
                                            <Badge variant="secondary">
                                                <HardDrive className="h-3 w-3 mr-1" />
                                                {taskData.fileSizeFormatted}
                                            </Badge>
                                        )}
                                    </div>
                                    
                                    <Button 
                                        onClick={handleDownload}
                                        className="w-full"
                                        size="lg"
                                    >
                                        <Download className="mr-2 h-4 w-4" />
                                        Download MP3
                                    </Button>
                                    
                                    <div className="flex justify-between text-xs text-gray-500 pt-2">
                                        <span className="flex items-center">
                                            <Clock className="h-3 w-3 mr-1" />
                                            {taskData.expiresText || 'Expires in 7 days'}
                                        </span>
                                        <span>
                                            {taskData.downloadCount} {taskData.downloadCount === 1 ? 'download' : 'downloads'}
                                        </span>
                                    </div>
                                </div>
                            </Card>
                        </div>
                    )}
                    
                    {/* Download History */}
                    {downloadHistory.length > 0 && (
                        <div className="mt-6">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-lg font-medium">Recent Downloads</h3>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                        downloadHistoryUtils.clearHistory();
                                        setDownloadHistory([]);
                                        toast({
                                            title: "History Cleared",
                                            description: "Download history has been cleared.",
                                        });
                                    }}
                                    className="text-red-600 hover:text-red-700"
                                >
                                    Clear All
                                </Button>
                            </div>
                            <div className="space-y-2">
                                {downloadHistory.slice(0, 3).map((historyItem) => (
                                    <Card key={historyItem.taskId} className="p-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3 flex-1 min-w-0">
                                                {historyItem.thumbnail && (
                                                    <img 
                                                        src={historyItem.thumbnail} 
                                                        alt={historyItem.title || 'Video'} 
                                                        className="h-10 w-16 object-cover rounded"
                                                    />
                                                )}
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium truncate">
                                                        {historyItem.title || 'Unknown Title'}
                                                    </p>
                                                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                                                        {historyItem.fileSizeFormatted && (
                                                            <span>{historyItem.fileSizeFormatted}</span>
                                                        )}
                                                        <span>•</span>
                                                        <span>{historyItem.downloadCount} downloads</span>
                                                    </div>
                                                </div>
                                            </div>
                                            {historyItem.downloadUrl && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => {
                                                        downloadHistoryUtils.updateDownloadCount(
                                                            historyItem.taskId, 
                                                            historyItem.downloadCount + 1
                                                        );
                                                        setDownloadHistory(downloadHistoryUtils.getHistory());
                                                        window.open(historyItem.downloadUrl, '_blank');
                                                    }}
                                                >
                                                    <Download className="h-3 w-3" />
                                                </Button>
                                            )}
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex justify-center text-xs text-muted-foreground">
                    Enter any YouTube video URL to convert it to MP3 format
                </CardFooter>
            </Card>
        </div>
    );
}