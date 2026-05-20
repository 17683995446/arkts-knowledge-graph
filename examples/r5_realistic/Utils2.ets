
export class Utils {
  validate(input: string): boolean {
    return input.length > 0
  }

  sanitize(input: string): string {
    return input.replace(/[^a-zA-Z0-9]/g, '')
  }
}
