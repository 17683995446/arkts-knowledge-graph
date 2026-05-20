
export class Utils {
  format(input: string): string {
    return input.trim()
  }

  parse(input: string): object {
    return JSON.parse(input)
  }
}
