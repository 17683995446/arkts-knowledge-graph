/**
 * 深度嵌套结构测试文件
 */

export class Outer0 {
    middle: Middle0 = new Middle0();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle0 {
    inner: Inner0 = new Inner0();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner0 {
    deeplyNested: DeeplyNested0 = new DeeplyNested0();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested0 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
