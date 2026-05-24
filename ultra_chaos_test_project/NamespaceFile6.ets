/**
 * 命名空间测试文件
 */

namespace Namespace6 {
    export const VERSION = '1.0.0';
    
    export class InternalClass {
        name: string;
        
        constructor(name: string) {
            this.name = name;
        }
        
        greet(): string {
            return `Hello, ${this.name}`;
        }
    }
    
    export function helper(): void {
        console.log('helper function');
    }
    
    export namespace Inner {
        export const INNER_CONST = 42;
    }
}

export class UsingNamespace6 {
    useHelper(): void {
        Namespace6.helper();
        const cls = new Namespace6.InternalClass('test');
        cls.greet();
    }
}
