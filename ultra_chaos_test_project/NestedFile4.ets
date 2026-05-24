/**
 * 深度嵌套结构测试文件
 */

export class Outer4 {
    middle: Middle4 = new Middle4();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle4 {
    inner: Inner4 = new Inner4();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner4 {
    deeplyNested: DeeplyNested4 = new DeeplyNested4();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested4 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
