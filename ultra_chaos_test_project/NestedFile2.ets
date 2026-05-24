/**
 * 深度嵌套结构测试文件
 */

export class Outer2 {
    middle: Middle2 = new Middle2();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle2 {
    inner: Inner2 = new Inner2();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner2 {
    deeplyNested: DeeplyNested2 = new DeeplyNested2();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested2 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
