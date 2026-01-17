export function formatDate(dateString: string | null | undefined): string {
    if (!dateString) return "";

    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

export function formatSource(source: any): { name: string; url: string | null } {
    if (typeof source === 'string') {
        return { name: source, url: null };
    }
    return {
        name: source.name || source.url || "Source",
        url: source.url || null
    };
}
