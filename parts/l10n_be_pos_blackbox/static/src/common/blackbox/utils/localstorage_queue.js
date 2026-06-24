export class LocalStorageQueue {
    constructor(storageKey) {
        this.storageKey = storageKey;
        this.queue = this._loadQueueFromStorage();
    }

    _loadQueueFromStorage() {
        const storedQueue = localStorage.getItem(this.storageKey);
        return storedQueue ? JSON.parse(storedQueue) : [];
    }

    _saveQueueToStorage() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.queue));
    }

    purge() {
        const allItems = this.queue.slice();
        this.clear();
        return allItems;
    }

    push(item) {
        this.queue.push(item);
        this._saveQueueToStorage();
    }

    clear() {
        this.queue = [];
        this._saveQueueToStorage();
    }
}
