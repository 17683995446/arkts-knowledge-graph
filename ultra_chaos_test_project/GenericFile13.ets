/**
 * 泛型测试文件
 */

interface GenericInterface<T, U> {
    getValue(): T;
    setValue(value: T): void;
}

export class GenericClass<T> {
    private data: T;
    
    constructor(initial: T) {
        this.data = initial;
    }
    
    getData(): T {
        return this.data;
    }
    
    setData(value: T): void {
        this.data = value;
    }
}

export class SpecificClass extends GenericClass<string> {
    constructor() {
        super('initial');
    }
    
    getUpperCase(): string {
        return this.getData().toUpperCase();
    }
}

export type Result<T, E = Error> = {
    ok: boolean;
    value?: T;
    error?: E;
};
