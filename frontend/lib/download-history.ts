// Download history utilities for localStorage persistence

export interface DownloadHistoryItem {
  taskId: string;
  title?: string;
  channel?: string;
  thumbnail?: string;
  fileSizeFormatted?: string;
  downloadUrl?: string;
  completedAt: string;
  downloadCount: number;
}

const STORAGE_KEY = 'yt-mp3-download-history';
const MAX_HISTORY_ITEMS = 20;

export const downloadHistoryUtils = {
  // Get download history from localStorage
  getHistory(): DownloadHistoryItem[] {
    if (typeof window === 'undefined') return [];
    
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error reading download history:', error);
      return [];
    }
  },

  // Add item to download history
  addToHistory(item: Omit<DownloadHistoryItem, 'completedAt'>): void {
    if (typeof window === 'undefined') return;
    
    try {
      const history = this.getHistory();
      const newItem: DownloadHistoryItem = {
        ...item,
        completedAt: new Date().toISOString(),
      };
      
      // Remove any existing item with the same taskId
      const filteredHistory = history.filter(h => h.taskId !== item.taskId);
      
      // Add new item to the beginning and limit the array
      const updatedHistory = [newItem, ...filteredHistory].slice(0, MAX_HISTORY_ITEMS);
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedHistory));
    } catch (error) {
      console.error('Error saving to download history:', error);
    }
  },

  // Update download count for an item
  updateDownloadCount(taskId: string, count: number): void {
    if (typeof window === 'undefined') return;
    
    try {
      const history = this.getHistory();
      const updatedHistory = history.map(item => 
        item.taskId === taskId 
          ? { ...item, downloadCount: count }
          : item
      );
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedHistory));
    } catch (error) {
      console.error('Error updating download count:', error);
    }
  },

  // Clear download history
  clearHistory(): void {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Error clearing download history:', error);
    }
  },

  // Remove expired items (older than 7 days)
  removeExpiredItems(): void {
    if (typeof window === 'undefined') return;
    
    try {
      const history = this.getHistory();
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      
      const validHistory = history.filter(item => 
        new Date(item.completedAt) > sevenDaysAgo
      );
      
      if (validHistory.length !== history.length) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(validHistory));
      }
    } catch (error) {
      console.error('Error removing expired items:', error);
    }
  },
};
