// Custom Error class to handle connection errors to the Blackbox (FDM)
export class L10nBeBlackboxConnectionError extends Error {
    constructor(message) {
        super(message);
    }
}
